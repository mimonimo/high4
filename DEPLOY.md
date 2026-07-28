# 배포 방법 (GitHub Pages)

1. GitHub에서 새 저장소 생성 (이름: high1-point-flow) — **Public** 필수
2. 이 폴더 전체를 push
   ```
   git init
   git add .
   git commit -m "HIGH1 POINT FLOW"
   git branch -M main
   git remote add origin https://github.com/<팀계정>/high1-point-flow.git
   git push -u origin main
   ```
3. 저장소 Settings → Pages → Branch를 **main / (root)** 선택 → Save
4. 1~2분 후 https://<팀계정>.github.io/high1-point-flow/ 접속
5. 시크릿 창에서 열어 정상 동작·모바일 확인

주의: data/ 폴더의 JSON이 반드시 함께 올라가야 함 (.gitignore가 이를 막지 않는지 확인)
