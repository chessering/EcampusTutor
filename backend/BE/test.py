# test_canvas_selenium.py
"""
Selenium 기반 Canvas 로그인 테스트

"""
from app.service.canvas_service import CanvasService


def test_canvas_login():
    """Canvas 로그인 테스트"""
    service = CanvasService()
    
    print("=" * 80)
    print("Canvas LMS 로그인 검증 테스트 (Selenium)")
    print("=" * 80)
    
    # 테스트 계정 (실제 정보로 교체)
    username = input("\nCanvas 아이디: ")
    password = input("Canvas 비밀번호: ")
    
    print("\n" + "=" * 80)
    print("로그인 검증 시작...")
    print("=" * 80 + "\n")
    
    # 로그인 시도
    result = service.verify_canvas_login(username, password)
    
    print("\n" + "=" * 80)
    if result:
        print("✅ 테스트 성공: Canvas 로그인 검증 완료!")
        print("🎉 이 계정으로 회원가입이 가능합니다.")
    else:
        print("❌ 테스트 실패: Canvas 로그인 검증 실패")
        print("💡 아이디와 비밀번호를 확인해주세요.")
    print("=" * 80)
    
    return result


def test_invalid_credentials():
    """잘못된 인증 정보 테스트"""
    service = CanvasService()
    
    print("\n" + "=" * 80)
    print("잘못된 인증 정보 테스트")
    print("=" * 80 + "\n")
    
    result = service.verify_canvas_login("invalid_user", "invalid_password")
    
    if not result:
        print("✅ 정상: 잘못된 인증 정보는 거부됨")
    else:
        print("❌ 오류: 잘못된 인증 정보가 통과됨")
    
    return not result


if __name__ == "__main__":
    print("\n🚀 Canvas 로그인 검증 테스트를 시작합니다...\n")
    print("⚠️ 주의: Selenium을 사용하므로 ChromeDriver가 필요합니다.")
    print("⚠️ 테스트 중 Chrome 브라우저가 백그라운드에서 실행됩니다.\n")
    
    # 실제 계정으로 테스트
    result1 = test_canvas_login()
    
    # 잘못된 계정으로 테스트
    print("\n잘못된 계정으로 테스트를 진행하시겠습니까? (y/n): ", end="")
    choice = input().lower()
    if choice == 'y':
        result2 = test_invalid_credentials()
    else:
        result2 = True
        print("잘못된 계정 테스트를 건너뜁니다.")
    
    print("\n" + "=" * 80)
    print("전체 테스트 결과")
    print("=" * 80)
    print(f"실제 계정 테스트: {'✅ 통과' if result1 else '❌ 실패'}")
    print(f"잘못된 계정 테스트: {'✅ 통과' if result2 else '❌ 실패'}")
    print("=" * 80)