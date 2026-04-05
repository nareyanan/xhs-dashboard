# 서버 세팅 가이드

## 1단계: Oracle Cloud 무료 서버 생성

1. https://cloud.oracle.com 접속 → 무료 계정 생성
2. 좌측 메뉴 → Compute → Instances → Create Instance
3. 설정:
   - Image: **Ubuntu 22.04**
   - Shape: **Ampere A1** (Always Free 표시 확인)
   - OCPUs: 2, Memory: 4GB (무료 한도)
   - SSH Key: 본인 공개키 등록
4. 생성 완료 후 공개 IP 확인

## 2단계: 방화벽 포트 열기 (Oracle Cloud)

Oracle Cloud Console → Virtual Cloud Network → Security Lists → Ingress Rules 추가:
- Port 8501 (대시보드), Source: 0.0.0.0/0

그리고 서버 내부 방화벽도 열기:
```bash
sudo iptables -I INPUT -p tcp --dport 8501 -j ACCEPT
sudo netfilter-persistent save
```

## 3단계: 서버에 Docker 설치

SSH 접속 후:
```bash
ssh ubuntu@<서버_IP>

# Docker 설치
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
newgrp docker

# Docker Compose 확인
docker compose version
```

## 4단계: 로컬 Mac에서 로그인 쿠키 생성

로컬 Mac 터미널에서:
```bash
cd xhs-dashboard
pip install playwright
playwright install chromium
python setup_login.py
```
→ 브라우저가 열리면 샤오훙슈에 로그인
→ data/cookies.json 파일 생성됨

## 5단계: 프로젝트 서버에 전송

```bash
# 로컬에서 실행
scp -r xhs-dashboard ubuntu@<서버_IP>:~/
```

## 6단계: 서버에서 실행

```bash
ssh ubuntu@<서버_IP>
cd xhs-dashboard

# .env 파일 생성
cp .env.example .env
# (필요 시 nano .env 로 수정)

# 빌드 및 실행
docker compose up -d --build

# 로그 확인
docker compose logs -f
```

## 7단계: 대시보드 접속

브라우저에서: `http://<서버_IP>:8501`

---

## 자주 쓰는 명령어

```bash
# 즉시 수집 실행 (테스트)
docker exec xhs-app python main.py --run-now

# 로그 보기
docker compose logs -f

# 재시작
docker compose restart

# 쿠키 만료 시 갱신 (로컬에서 다시 setup_login.py 실행 후)
scp data/cookies.json ubuntu@<서버_IP>:~/xhs-dashboard/data/
docker compose restart
```

## 쿠키 만료 주기

보통 1~3개월. 만료되면 로그에 아래 메시지 출력:
```
로그인 세션 만료! 쿠키를 갱신하세요: python setup_login.py
```
→ 로컬에서 setup_login.py 재실행 → 쿠키 파일 서버에 복사
