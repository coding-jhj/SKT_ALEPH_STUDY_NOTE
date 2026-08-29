<div align="center">

# SKT ALEPH 학습 노트

**IT 인프라 · 보안 과정을 책 한 권으로**

수업 노트와 강사 슬라이드 188강 원문이 한 곳에. 검색되고, 인쇄되고, 링크로 열립니다.

### [📖 읽으러 가기](https://coding-jhj.github.io/SKT_ALEPH_STUDY_NOTE/)

![chapters](https://img.shields.io/badge/28장-117만자-8a5a2b?style=flat-square)
![lectures](https://img.shields.io/badge/핵심키워드-188강_전량-8a5a2b?style=flat-square)
![code](https://img.shields.io/badge/코드블록-2%2C055-6b6459?style=flat-square)
![tables](https://img.shields.io/badge/표-1%2C323-6b6459?style=flat-square)
![pages](https://img.shields.io/badge/GitHub_Pages-live-2ea043?style=flat-square)

</div>

<br>

## 무엇이 들어 있나

|  | 분량 | 성격 |
|---|---|---|
| 🧪 **수업 노트** 6편 | 42만자 | 직접 실습한 기록. 명령·출력·에러와 원인까지 |
| 📚 **핵심키워드** 188강 | 72만자 | 강사 슬라이드 본문. 요약 없이 그대로 |
| 🗺️ **지도 · 부록** | 3만자 | 커리큘럼 분류 · 명령어 색인 · 용어집 · 공식 문서 대조 |

**수업 노트**는 *내가 해보니 이랬다*, **핵심키워드**는 *강사가 이렇게 설명했다*.
둘이 어긋나는 곳은 부록에 따로 모았습니다.

<br>

## 목차

| 부 | 장 | |
|---|---|---|
| 들어가기 | `01–03` | 사용법 · 커리큘럼 지도 · 과정 개요 |
| 네트워크 | `04–05` | 라우팅 · ACL · NAT · VPN · 통합 Lab |
| 리눅스 서버 | `06–09` | Rocky 9 서버랩 · NFS/Samba/SELinux · 커널 · Kali |
| 데이터베이스 | `10–11` | MariaDB SQL·백업·복제 · 원격 연동 |
| 핵심키워드 | `12–24` | 네트워크 52 · 리눅스 35 · 윈도우 6 · DB 9 · 모니터링 8 · 파이썬 4 · 보안 74 |
| 부록 | `25–28` | 중복과 상충 · 공식 문서 대조 · 명령어 색인 · 용어집 |

<br>

## 읽는 법

| | |
|---|---|
| 🔍 **검색** | 사이드바 검색창에 단어 → 목차가 걸러집니다 |
| 🧭 **위치** | 보고 있는 장은 소제목까지 펼쳐지고, 읽는 위치가 따라옵니다 |
| 🌗 **테마** | 라이트 / 다크 자동 |
| 🖨️ **인쇄** | 사이드바가 빠지고 본문만. PDF로 저장하면 그대로 교재 |

<br>

## 표기

| | |
|---|---|
| ✅ | 실행하고 출력까지 확인함 |
| ⚠️ | 실제로 난 오류, 빠지기 쉬운 함정 |
| 📘 | 수업 밖에서 공식 문서로 보강함 |
| ★ | 자주 틀리는 지점 |

출처가 불확실하면 적지 않습니다. 기억으로 채우지 않고 `확인 필요`로 남깁니다.

<br>

---

<details>
<summary><b>🛠 만드는 쪽</b> — 저장소를 고칠 사람만 보면 됩니다</summary>

<br>

### 폴더

```
notes/       수업 노트 — 사람이 쓴 마크다운
slides/      핵심키워드 188강 — PDF 자동 추출 (직접 고치지 마십시오)
book/        사용법 · 커리큘럼 지도 · 부록
docs/        빌드 결과. GitHub Pages가 이 폴더를 서비스합니다

build.py            notes + slides + book  →  docs/*.html
import_slides.py    핵심키워드 PDF zip     →  slides/*.md
pdf_blocks.py       PDF 한 쪽 → 제목·본문·코드·표
make_index.py       부록 「명령어 색인」 자동 생성
```

`notes/`와 `slides/`가 원본, `docs/`는 조립 결과입니다. 같은 내용을 두 곳에 두지 않습니다.

### 빌드

```bash
python build.py
python -m http.server 8899 --bind 127.0.0.1 --directory docs   # 로컬 확인
```

푸시하면 Pages가 1분 안에 반영합니다.

### 수업이 끝날 때마다

```bash
# 1) notes/2026-09-01_주제.md 추가
# 2) build.py 의 ORDER 에 한 줄
# 3) make_index.py 의 NOTE_LABEL 에 짧은 이름 (색인 표기용)
python build.py && git add -A && git commit -m "9/1 수업 노트" && git push
```

`build.py`가 알아서 하는 것 — 장 제목 승격, 한글 앵커 id, 사이드바 목차,
이전/다음 이동, 인쇄 배치, 명령어 색인 재생성.
그리고 **본문의 HTML 태그를 전부 글자로 막습니다.** 노트에 XSS 실습
페이로드가 실려 있어서, 막지 않으면 노트를 여는 순간 실행됩니다.

### 슬라이드 다시 가져오기

```bash
python import_slides.py "<핵심키워드 zip 경로>" && python build.py
```

PDF에는 무엇이 제목이고 무엇이 코드인지 표시가 없습니다. 이 꾸러미는
**글자 크기가 곧 구조**라서 그것으로 복원합니다.

| 크기 | 정체 | → |
|---|---|---|
| `30pt` | 쪽마다 반복되는 문서 제목 | 버림 |
| `18pt` | 대제목 `1.` | `###` |
| `15pt` | 소제목 `1-1.` | `####` |
| `12pt` | 본문 | 문단 |
| `8~9pt` DejaVuSansMono | 터미널 화면 | 코드블록 |
| `7.5pt` | 머리말 · 쪽번호 | 버림 |

표는 `find_tables(strategy="lines_strict")`. 기본값 `lines`는 칸 선이 아니라
글자 배치까지 선으로 쳐서 4열 5행 표를 6열 7행으로 깨뜨립니다.

줄바꿈은 문서 전체 낱말 사전으로 복원합니다. 붙여 만든 낱말이 문서 어딘가에
온전히 나오면 붙이고, 아니면 공백을 넣습니다.

### 한계

- **그림 없음** — 이 꾸러미 188강 PDF에는 이미지가 0개입니다
- **강의 번호가 건너뜁니다** — 주제별로 묶은 탓. 001~188강 전부 들어 있습니다

</details>
