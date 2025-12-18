import sys
import time
import os
import urllib.parse
import requests
import traceback
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from tqdm import tqdm
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

from dotenv import load_dotenv
load_dotenv()


# ---------- 설정 ----------
CHROME_DRIVER_PATH = None
HEADLESS = True
DOWNLOAD_DIR = os.getenv("WORKDIR")
# --------------------------
if not DOWNLOAD_DIR:
    raise ValueError("WORKDIR 환경변수는 필수입니다")

MIN_CONTENT_LENGTH = 5_000_000  # 5MB 이상이면 본영상일 확률 높음
BLACKLIST = ("preloader", "intro", "teaser", "preview", "ad")


def start_driver(headless=HEADLESS):

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,900")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--autoplay-policy=user-gesture-required")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.cookies": 1,
        "profile.block_third_party_cookies": False,
    })
    chrome_options.add_argument("--disable-features=BlockThirdPartyCookies")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")

    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--hide-scrollbars")
    return webdriver.Chrome(options=chrome_options)

def automatic_login(driver, login_page_url, username, password,
                    username_selector, password_selector, submit_selector,
                    wait_after_submit=6):
    try:
        driver.get(login_page_url)
        time.sleep(1)
        user_el = driver.find_element(By.CSS_SELECTOR, username_selector)
        pass_el = driver.find_element(By.CSS_SELECTOR, password_selector)
        user_el.clear(); user_el.send_keys(username)
        pass_el.clear(); pass_el.send_keys(password)
        if submit_selector:
            element = driver.find_element(By.CSS_SELECTOR, submit_selector)
            driver.execute_script("arguments[0].click();", element)
        time.sleep(wait_after_submit)
        return True
    except Exception as e:
        print("자동 로그인 실패:", e)
        return False


def find_candidate_media_urls(driver, wait_seconds=5):
    time.sleep(wait_seconds)
    seen = []
    for req in driver.requests:
        try:
            url = req.url
        except Exception:
            continue
        if not url:
            continue
        low = url.lower()
        if ".mp4" in low or ".m3u8" in low or ".mpd" in low:
            if url not in seen:
                seen.append(url)
    return seen

def extract_cookie_header_from_driver(driver):
    cookies = driver.get_cookies()
    if not cookies:
        return None
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])


def download_stream_with_requests(url, headers, out_path, chunk_size=1024*1024):
    try:
        print(f"다운로드 시작: {url}")
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
            with open(out_path, "wb") as f, tqdm(total=total, unit="B", unit_scale=True, desc=os.path.basename(out_path)) as pbar:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        print("다운로드 완료:", out_path)
    except Exception as e:
        print("다운로드 중 오류 발생:", e)
        sys.exit(1)
        

def extract_commons_iframe_src(driver, timeout=15):
    frames = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.TAG_NAME,"iframe"))
    )
    for f in frames:
        src=(f.get_attribute("src") or "").lower()
        if "commons.khu.ac.kr" in src:
            return f.get_attribute("src")
    for f in frames:
        try:
            driver.switch_to.frame(f)
            inner = driver.find_elements(By.TAG_NAME,"iframe")
            for ff in inner:
                src=(ff.get_attribute("src") or "").lower()
                if "commons.khu.ac.kr" in src:
                    ret=ff.get_attribute("src")
                    driver.switch_to.default_content(); return ret
            driver.switch_to.default_content()
        except:
            driver.switch_to.default_content()
    return None

# -------------------- Playback helpers --------------------
def install_video_debugger(driver):
    js = """
    (function(){
      if (window.__video_debug_installed) return;
      const v = document.querySelector('video');
      if (!v) return;
      window.__video_debug_installed = true;
      const log = (...a)=>console.log('[VIDEO]', ...a);
      ['play','playing','pause','waiting','stalled','error','abort','emptied',
       'ended','loadedmetadata','loadeddata','timeupdate','ratechange','volumechange'].forEach(ev=>{
         v.addEventListener(ev, ()=>log('event', ev, {ct:v.currentTime, rs:v.readyState, ns:v.networkState, src:v.currentSrc}));
       });
      v.addEventListener('error', ()=> {
        const e = v.error;
        if (e) log('mediaError', e && e.code, e && e.message);
      });
    })();
    """
    try:
        driver.execute_script(js)
    except Exception:
        pass

def js_force_play(driver):
    js = """
    const v = document.querySelector('video');
    if (!v) return 'no-video';
    try {
      v.muted = true;
      v.setAttribute('playsinline','');
      v.autoplay = true;
      const p = v.play();
      if (p && typeof p.then === 'function') {
        return p.then(()=> 'ok').catch(err => 'play-reject:' + (err && err.name) + ':' + (err && err.message));
      }
      return 'ok';
    } catch (e) {
      return 'play-throw:' + e.name + ':' + e.message;
    }
    """
    try:
        return driver.execute_script(js)
    except Exception as e:
        return f"play-exec-error:{e}"

def get_video_state(driver):
    js = """
    const v = document.querySelector('video');
    if (!v) return null;
    return {paused:v.paused, ct:v.currentTime, rs:v.readyState, ns:v.networkState, src:v.currentSrc||v.src||null};
    """
    try:
        return driver.execute_script(js)
    except Exception:
        return None

def click_center(el, driver):
    try:
        size = el.size
        ActionChains(driver).move_to_element_with_offset(el, max(size['width']//2 - 1, 1), max(size['height']//2 - 1, 1))\
                            .pause(0.05).click().pause(0.05).perform()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", el)
        except Exception:
            pass

def bring_into_view_and_focus(el, driver):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].focus && arguments[0].focus();", el)
    except Exception:
        pass

def try_user_gestures(driver):
    selectors = [
        "div.vc-front-screen-play-btn",
        ".player-center-control-wrapper",
        "video"
    ]
    for sel in selectors:
        try:
            el = WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
            bring_into_view_and_focus(el, driver)
            click_center(el, driver)
            time.sleep(0.2)
        except Exception:
            continue
    # 키보드 토글
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        for key in [Keys.SPACE, 'k', Keys.SPACE]:
            body.send_keys(key)
            time.sleep(0.15)
    except Exception:
        pass

def ensure_playing_strong(driver):
    install_video_debugger(driver)
    try_user_gestures(driver)
    res = js_force_play(driver)
    print("js_force_play:", res)

    ok_tick = 0
    for i in range(14):  # 약 7초 관찰
        st = get_video_state(driver)
        print("video state:", st)
        if st and st.get('ct', 0) > 0.5 and st.get('rs', 0) >= 2:
            ok_tick += 1
            if ok_tick >= 2:
                print("✅ 재생 확인 (currentTime 진행)")
                return True
        else:
            try_user_gestures(driver)
            if i in (3, 7, 10):
                res = js_force_play(driver)
                print("js_force_play(retry):", res)
        time.sleep(0.5)
    print("⚠️ 재생 확인 실패(시간 진행 없음)")
    return False

# ----- src 교체 감지 후 즉시 재재생 + 최종 URL 확보 -----
def ensure_resume_after_src_swap(driver, watch_sec=45, poll=0.5):
    """
    intro → 본영상으로 src 교체되는 순간, 사용자 제스처 + JS play()를
    즉시 재시도하여 재생을 붙인다. 성공 시 (currentSrc, currentTime) 반환.
    실패 시 (None, 0.0)
    """
    def js_touch_and_play():
        js = """
        const v = document.querySelector('video');
        if (!v) return 'no-video';
        try {
          v.muted = true;
          v.setAttribute('playsinline','');
          v.autoplay = true;
          const p = v.play();
          if (p && typeof p.then === 'function') {
            return p.then(()=> 'ok').catch(err => 'reject:'+ (err && err.name));
          }
          return 'ok';
        } catch(e) { return 'throw:'+e.name; }
        """
        return driver.execute_script(js)

    def user_gesture():
        try:
            v = driver.find_element(By.TAG_NAME, "video")
            ActionChains(driver).move_to_element_with_offset(
                v, max(v.size['width']//2-1,1), max(v.size['height']//2-1,1)
            ).click().perform()
        except: pass
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            for key in [Keys.SPACE, 'k', Keys.SPACE]:
                body.send_keys(key); time.sleep(0.1)
        except: pass

    prev_src = None
    ok_tick = 0
    t0 = time.time()
    while time.time() - t0 < watch_sec:
        st = get_video_state(driver)
        print("watch:", st)
        if not st:
            time.sleep(poll); continue

        cur_src = st.get('src') or ''
        ct = st.get('ct') or 0.0
        rs = st.get('rs') or 0

        # src가 바뀌는 순간 또는 멈춰있으면 즉시 재재생 시도
        if prev_src != cur_src or (ct == 0 and rs <= 1):
            user_gesture()
            res = js_touch_and_play()
            print("replay_on_swap:", res)

        if ct > 0.5 and rs >= 2:
            ok_tick += 1
            if ok_tick >= 2:
                return (cur_src, ct)
        else:
            ok_tick = 0

        prev_src = cur_src
        time.sleep(poll)

    return (None, 0.0)

def main_workflow(video_page_url,
    login_page_url=None, username=None, password=None, username_selector=None, password_selector=None, submit_selector=None,
    headless=HEADLESS):
    
    try:
        
        print("다운로드 경로:", DOWNLOAD_DIR)
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

        driver = start_driver(headless=headless)
        try:
            # 1) 로그인 (무조건 자동 로그인 시도)
            if username and password and username_selector and password_selector:
                print("자동 로그인 시도...")
                ok = automatic_login(driver, login_page_url or video_page_url,
                    username, password, username_selector, password_selector, submit_selector)

            # 2) 비디오 페이지 로드
            print("비디오 페이지 로드:", video_page_url)
            driver.get(video_page_url)
            time.sleep(10)

            # 3) 모든 iframe 찾기
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"발견된 iframe 개수: {len(iframes)}")
                
            for idx, iframe in enumerate(iframes):
                print(f"iframe {idx}: src='{iframe.get_attribute('src')}'")

            # 4) iframe으로 전환 (iframe[1] -> inner_frame)
            driver.switch_to.frame(1)
            inner_iframes = driver.find_elements(By.TAG_NAME, "iframe")
            print(f"발견된 inner iframe 개수: {len(inner_iframes)}")
            for idx, inner_iframe in enumerate(inner_iframes):
                print(f"inner_iframe {idx}: src='{inner_iframe.get_attribute('src')}'")
                
            if inner_iframes:
                driver.switch_to.frame(inner_iframes[0])
            else:
                print("no inner")
                driver.quit()
                sys.exit(1)
                
            time.sleep(3)
            try:
                ensure_playing_strong(driver)
            except Exception as e:
                print("❌ 재생 버튼 클릭 실패:", e)
                traceback.print_exc()
                driver.quit()
                sys.exit(1)

            
            # 3) 네트워크 요청 캡처
            candidates = find_candidate_media_urls(driver, wait_seconds=7)
            if not candidates:
                print("미디어 URL을 찾지 못했습니다.")
                sys.exit(1)

            print("발견된 후보 URL들:")
            for i, u in enumerate(candidates):
                print(f" {i}: {u}")
                
            if (len(candidates) <= 2):
                try:
                    ensure_resume_after_src_swap(driver)
                    time.sleep(3)
                except Exception as e:
                    print("재시작 실패:", type(e).__name__, "-", str(e))
                    traceback.print_exc()

            # 우선순위 선택
            selected = candidates[-1]

            print("선택된 URL:", selected)

            headers = {"User-Agent": "Mozilla/5.0"}
            cookie_header = extract_cookie_header_from_driver(driver)
            if cookie_header:
                headers["Cookie"] = cookie_header
            headers["Referer"] = "https://commons.khu.ac.kr/"

            # 4) manifest 처리
            el = driver.find_element(By.CSS_SELECTOR, "span.vc-content-meta-title-text")
            title_text = el.get_attribute("title")

            # 파일명으로 쓸 수 없는 문자 제거 (윈도우 기준 \/:*?"<>|)
            safe_name = "".join(c for c in title_text if c not in '\\/:*?"<>|')
            out_name = f"{safe_name}.mp4"
            out_path = os.path.join(DOWNLOAD_DIR, out_name)
            download_stream_with_requests(selected, headers, out_path)
            return {"status": "downloaded", "path": out_path}

        finally:
            driver.switch_to.parent_frame()
            driver.switch_to.default_content()
            driver.quit()
    except Exception as e:
        print("예상치 못한 오류 발생:", e)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # ----- 여기에 본인 로그인 정보/셀렉터 직접 설정 -----
    video_page_url = os.getenv("VIDEO_PAGE_URL")
    login_page_url = os.getenv("CANVAS_LOGIN_URL")
    
    #video url 더미데이터
    #https://khcanvas.khu.ac.kr/courses/80236/modules/items/4562523?return_url=/courses/80236/external_tools/196
    #https://khcanvas.khu.ac.kr/courses/80236/modules/items/4562520?return_url=/courses/80236/external_tools/196


    username = os.getenv("CANVAS_USERNAME")
    password = os.getenv("CANVAS_PASSWORD")
    username_selector = "input#login_user_id"   # Canvas 로그인 아이디 입력창
    password_selector = "input#login_user_password"    # Canvas 로그인 비밀번호 입력창
    submit_selector   = "a"   # 로그인 버튼
    # --------------------------------------------

    print("DEBUG URL:", video_page_url)
    print("DEBUG ID:", username)
    print("DEBUG PW:", password)
    res = main_workflow(video_page_url,
                        login_page_url=login_page_url,
                        username=username,
                        password=password,
                        username_selector=username_selector,
                        password_selector=password_selector,
                        submit_selector=submit_selector,
                        headless=True)

    print("결과:", res)
