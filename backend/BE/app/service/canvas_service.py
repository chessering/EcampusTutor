# app/service/canvas_service.py (Selenium 동기 버전)
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class CanvasService:
    def __init__(self):
        self.canvas_url = "https://khcanvas.khu.ac.kr"
        self.login_url = "https://e-campus.khu.ac.kr/xn-sso/login.php"
        
    def _create_driver(self, headless: bool = True):
        """Chrome 드라이버 생성"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1280,900")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--hide-scrollbars")
        
        return webdriver.Chrome(options=chrome_options)
    
    def verify_canvas_login(self, username: str, password: str) -> bool:
        """
        Canvas LMS 로그인 검증 (Selenium 사용 - 동기 버전)
        
        Args:
            username: Canvas 사용자 아이디
            password: Canvas 비밀번호
            
        Returns:
            bool: 로그인 성공 여부
        """
        driver = None
        try:
            print(f"🔍 Canvas 로그인 검증 시작 (사용자: {username})")
            driver = self._create_driver(headless=True)
            
            # 1. 로그인 페이지 접속
            full_login_url = (
                f"{self.login_url}?auto_login=&sso_only=&cvs_lgn=&"
                f"return_url=https%3A%2F%2Fe-campus.khu.ac.kr%2Fxn-sso%2Fgw-cb.php"
                f"%3Ffrom%3D%26login_type%3Dstandalone%26return_url%3D"
                f"https%253A%252F%252Fe-campus.khu.ac.kr%252Flogin%252Fcallback"
            )
            
            print(f"🌐 로그인 페이지 접속 중...")
            driver.get(full_login_url)
            time.sleep(2)
            
            # 2. 로그인 폼 요소 찾기
            try:
                username_input = driver.find_element(By.CSS_SELECTOR, "input#login_user_id")
                password_input = driver.find_element(By.CSS_SELECTOR, "input#login_user_password")
                submit_button = driver.find_element(By.CSS_SELECTOR, "a")  # 로그인 버튼
                
                print(f"✅ 로그인 폼 발견")
            except NoSuchElementException as e:
                print(f"❌ 로그인 폼을 찾을 수 없음: {e}")
                return False
            
            # 3. 로그인 정보 입력
            print(f"📝 로그인 정보 입력 중...")
            username_input.clear()
            username_input.send_keys(username)
            
            password_input.clear()
            password_input.send_keys(password)
            
            # 4. 로그인 버튼 클릭
            print(f"🔐 로그인 시도 중...")
            driver.execute_script("arguments[0].click();", submit_button)
            
            # 5. 로그인 결과 대기
            time.sleep(6)
            
            # 6. 로그인 성공 여부 확인
            current_url = driver.current_url.lower()
            print(f"📍 현재 URL: {current_url}")
            
            # 성공 시나리오
            success_indicators = [
                "e-campus.khu.ac.kr" in current_url and "login" not in current_url,
                "khcanvas.khu.ac.kr" in current_url,
                "dashboard" in current_url,
                "courses" in current_url,
            ]
            
            # 실패 시나리오
            failure_indicators = [
                "login" in current_url and "xn-sso" in current_url,
            ]
            
            # 페이지 소스에서 에러 메시지 확인
            try:
                page_source = driver.page_source.lower()
                error_keywords = [
                    "아이디 또는 비밀번호",
                    "로그인 실패",
                    "잘못된",
                    "incorrect",
                    "invalid",
                    "failed",
                ]
                
                if any(keyword in page_source for keyword in error_keywords):
                    print("❌ Canvas 로그인 실패 - 에러 메시지 감지")
                    return False
            except Exception:
                pass
            
            # 성공 판단
            if any(success_indicators) and not any(failure_indicators):
                print("✅ Canvas 로그인 성공!")
                return True
            
            if any(failure_indicators):
                print("❌ Canvas 로그인 실패 - 로그인 페이지에 머물러 있음")
                return False
            
            # 쿠키 확인
            cookies = driver.get_cookies()
            session_cookies = [c for c in cookies if 'session' in c.get('name', '').lower()]
            
            if session_cookies:
                print(f"✅ 세션 쿠키 발견 ({len(session_cookies)}개) - 로그인 성공!")
                return True
            
            print("❌ Canvas 로그인 실패 - 성공 지표를 찾을 수 없음")
            return False
            
        except TimeoutException:
            print("⏱️ 타임아웃: Canvas 페이지 로드 실패")
            return False
        except Exception as e:
            print(f"❌ 예기치 않은 오류 발생: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if driver:
                try:
                    driver.quit()
                    print("🔌 브라우저 종료")
                except Exception:
                    pass