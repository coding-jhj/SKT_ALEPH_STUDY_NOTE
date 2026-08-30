# MariaDB 실습 학습 노트

## SQL 기초 → 문자셋 → 논리 백업·복원 → 표준 복제

**작성 기준일:** 2026-08-27  
**기반 자료:** 2026-08-27 오전 수업 필기 260827-정환주.txt  
**실습 환경 기록:** Rocky Linux, MariaDB 10.5.29, firewalld

이 노트는 원문 필기의 중복을 제거하고 오타·누락·잘못된 성공 판정을 바로잡은 학습용 교재다. 최신 MariaDB와 firewalld 공식 문서를 대조했지만, 실습 명령은 필기에 기록된 MariaDB 10.5.29 환경과 수업에서 사용한 legacy 명령을 기준으로 설명한다.

---

## 목차

1. [이번 수업의 전체 구조](#1-이번-수업의-전체-구조)
2. [터미널과 MariaDB 프롬프트](#2-터미널과-mariadb-프롬프트)
3. [MariaDB 서비스와 클라이언트](#3-mariadb-서비스와-클라이언트)
4. [데이터베이스와 테이블](#4-데이터베이스와-테이블)
5. [문자셋과 한글 입력 오류](#5-문자셋과-한글-입력-오류)
6. [INSERT와 SELECT](#6-insert와-select)
7. [조건 검색·정렬·집계](#7-조건-검색정렬집계)
8. [백업과 복원](#8-백업과-복원)
9. [firewalld와 원격 접속](#9-firewalld와-원격-접속)
10. [migration과 replication](#10-migration과-replication)
11. [binary log와 복제 설정값](#11-binary-log와-복제-설정값)
12. [표준 복제 실습의 올바른 순서](#12-표준-복제-실습의-올바른-순서)
13. [복제 상태 확인과 성공 판정](#13-복제-상태-확인과-성공-판정)
14. [필기 오류·누락·혼동 정리](#14-필기-오류누락혼동-정리)
15. [오류 진단 순서](#15-오류-진단-순서)
16. [최종 체크리스트와 공식 자료](#16-최종-체크리스트와-공식-자료)

---

# 1. 이번 수업의 전체 구조

이번 수업은 다음 네 단계가 연결된 내용이다.

| 단계 | 배운 내용 | 핵심 질문 |
|---|---|---|
| 1 | SQL 기초 | 데이터베이스·테이블을 만들고 데이터를 어떻게 다루는가? |
| 2 | 문자셋 | 왜 한글 INSERT가 실패했고, 어디를 utf8mb4로 바꿔야 하는가? |
| 3 | 백업·복원 | 데이터베이스와 테이블을 SQL 파일로 저장하고 되살리는 방법은 무엇인가? |
| 4 | 표준 복제 | 한 서버의 변경을 다른 서버가 어떻게 계속 따라가는가? |

학습 흐름은 다음과 같다.

1. 문자셋을 명시하여 데이터베이스와 테이블을 만든다.
2. INSERT로 데이터를 넣고 SELECT·WHERE·ORDER BY·LIMIT로 조회한다.
3. COUNT·SUM·AVG·MIN·MAX로 집계한다.
4. mariadb-dump로 논리 백업을 만들고 복원한다.
5. primary의 binary log를 활성화한다.
6. 복제 계정과 TCP 3306 통신을 준비한다.
7. replica를 초기 데이터로 맞춘다.
8. dump 시점에 대응하는 binary log 파일·위치로 연결한다.
9. I/O thread와 SQL thread가 모두 실행 중인지 확인한다.
10. primary에서만 새 데이터를 생성하고 replica에서 자동 반영을 확인한다.

## 원문에서 확인되는 사실

- library 데이터베이스와 books 테이블을 만들었다.
- AUTO_INCREAMENT 오타로 첫 CREATE TABLE이 실패했고 AUTO_INCREMENT로 다시 실행하여 성공했다.
- 데미안 한글 INSERT가 Incorrect string value로 실패했다.
- 영문 책 데이터 세 건은 INSERT되었다.
- 데이터베이스 하나, 전체 데이터베이스, 특정 테이블의 dump 파일을 만들었다.
- binary log 관련 설정, 복제 계정, 방화벽 3306, CHANGE MASTER TO, START SLAVE를 실습했다.

## 원문만으로 확인할 수 없는 사실

- SHOW SLAVE STATUS의 실제 출력이 기록되어 있지 않다.
- Slave_IO_Running과 Slave_SQL_Running이 Yes였는지 확인할 수 없다.
- replica에서 나중에 직접 만든 replitest가 복제로 생성되었다고 볼 수 없다.
- MASTER_HOST와 MASTER_LOG_FILE·MASTER_LOG_POS가 기록 구간마다 서로 다르다.

따라서 “명령을 입력했다”와 “복제가 성공했다”를 반드시 구분해야 한다.

---

# 2. 터미널과 MariaDB 프롬프트

## 2.1 Linux 셸

```text
[root@web ~]#
```

이 화면에서는 운영체제 명령을 입력한다.

```bash
systemctl start mariadb
ls
ls -l
vi /etc/my.cnf.d/mariadb-server.cnf
firewall-cmd --reload
mysqldump -u root -p library > backup.sql
```

프롬프트의 첫 root는 Linux 사용자이고 web은 Linux 호스트 이름이다.

## 2.2 MariaDB 클라이언트

```text
MariaDB [(none)]>
```

이 화면에서는 SQL을 입력한다.

```sql
CREATE DATABASE library;
SHOW DATABASES;
USE library;
SELECT * FROM books;
```

none은 아직 현재 데이터베이스를 선택하지 않았다는 의미다.

```text
MariaDB [library]>
```

USE library를 실행하여 현재 세션의 데이터베이스가 library가 된 상태다.

## 2.3 세미콜론과 화살표 프롬프트

```text
MariaDB [library]> SELECT *
    -> FROM books
    -> WHERE available = TRUE
    -> ;
```

화살표가 나오는 것은 SQL 문장이 아직 끝나지 않았다는 뜻이다. 세미콜론 또는 역슬래시 g를 입력하면 실행되고, 잘못 입력했다면 역슬래시 c로 현재 문장을 취소할 수 있다.

---

# 3. MariaDB 서비스와 클라이언트

## 3.1 역할 구분

| 구성요소 | 역할 |
|---|---|
| MariaDB 서버 서비스 | 데이터 파일을 관리하고 SQL을 실행하며 네트워크 포트를 수신 |
| MariaDB 클라이언트 | 서버에 접속하여 SQL을 전달하고 결과를 표시 |
| mariadb-dump | 구조와 데이터를 SQL 텍스트로 추출하는 논리 백업 도구 |
| firewalld | 운영체제 수준에서 네트워크 연결을 허용·차단하는 방화벽 |

## 3.2 서비스 명령

```bash
# 현재 한 번 시작
systemctl start mariadb

# 부팅 시 자동 시작 등록
systemctl enable mariadb

# 지금 시작하고 부팅 시 자동 시작
systemctl enable --now mariadb

# 상태 확인
systemctl status mariadb
systemctl is-active mariadb

# 설정 변경 후 재시작
systemctl restart mariadb
```

start와 enable은 다른 기능이다. start만 하면 현재 부팅에서 실행되지만 다음 부팅 때 자동 시작된다는 보장은 없다.

재시작 실패 시:

```bash
journalctl -u mariadb -n 100 --no-pager
```

## 3.3 접속 명령

```bash
mariadb -u root -p
```

수업에서 사용한 다음 이름도 Linux에서 호환 이름으로 동작할 수 있다.

```bash
mysql -u root -p
```

현재 MariaDB 공식 문서는 mariadb와 mariadb-dump를 중심으로 설명하며, mysql과 mysqldump는 기존 호환 명칭으로 남아 있다.

## 3.4 셸 리다이렉션

| 기호 | 의미 | 예 |
|---|---|---|
| > | 명령 출력을 파일로 새로 만들거나 덮어씀 | mariadb-dump ... > backup.sql |
| >> | 파일 끝에 출력 추가 | 로그 추가 |
| < | 파일을 명령의 입력으로 전달 | mariadb ... < backup.sql |

리다이렉션은 SQL 문법이 아니라 Linux 셸 문법이다.

---

# 4. 데이터베이스와 테이블

## 4.1 데이터베이스 생성·선택

수업의 기본 명령:

```sql
CREATE DATABASE library;
SHOW DATABASES;
USE library;
SELECT DATABASE();
```

한글 데이터가 들어갈 데이터베이스는 처음부터 문자셋과 콜레이션을 지정한다.

```sql
CREATE DATABASE library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

이미 존재할 수 있다면 IF NOT EXISTS를 사용한다.

```sql
CREATE DATABASE IF NOT EXISTS library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

데이터베이스의 문자셋은 새 테이블에 물려주는 기본값이다. 이미 만들어진 테이블의 문자셋까지 자동으로 바꾸지는 않는다.

## 4.2 테이블 생성

수업에서 의도한 구조:

```sql
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(50),
    published_year INT,
    available BOOLEAN DEFAULT TRUE
);
```

한글 저장을 명시한 권장 형태:

```sql
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(50),
    published_year INT,
    available BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

## 4.3 열 정의

| 요소 | 의미 |
|---|---|
| id | 행을 구별할 열 |
| INT | 정수형 |
| AUTO_INCREMENT | 새 행의 id를 자동 증가 |
| PRIMARY KEY | 행을 유일하게 식별하는 키 |
| VARCHAR(100) | 최대 길이 100의 가변 문자열 |
| NOT NULL | 반드시 값이 있어야 함 |
| DEFAULT TRUE | 값을 생략하면 TRUE 사용 |
| BOOLEAN | MariaDB에서는 TINYINT(1)의 별칭 |

AUTO_INCREMENT와 PRIMARY KEY를 함께 쓰면 사용자가 id를 매번 직접 정하지 않아도 되고, 각 행을 유일하게 식별할 수 있다.

## 4.4 첫 번째 오류

잘못된 표현:

```sql
id INT AUTO_INCREAMENT PRIMARY KEY
```

올바른 표현:

```sql
id INT AUTO_INCREMENT PRIMARY KEY
```

AUTO_INCREAMENT는 존재하지 않는 키워드이므로 데이터 문제가 아니라 SQL 구문 오류가 발생한다.

## 4.5 구조 확인

```sql
SHOW TABLES;
DESC books;
DESCRIBE books;
SHOW CREATE TABLE books;
```

DESC는 열의 큰 구조를 보여 주고, SHOW CREATE TABLE은 엔진·문자셋·콜레이션·제약조건까지 확인하기 좋다.

BOOLEAN이 DESC에서 tinyint(1)로 보이는 것은 정상이다. TRUE는 보통 1, FALSE는 0으로 저장되고 조회된다.

---

# 5. 문자셋과 한글 입력 오류

## 5.1 문자셋과 콜레이션

| 개념 | 역할 |
|---|---|
| 문자셋 | 문자를 어떤 바이트 표현으로 저장·전달할지 결정 |
| 콜레이션 | 같은 문자셋의 문자열을 비교·정렬하는 규칙 |

utf8mb4는 유니코드 문자를 최대 4바이트로 저장할 수 있어 한국어와 이모지를 함께 고려할 수 있다. utf8을 막연히 사용하기보다 utf8mb4를 명시하는 것이 안전하다.

## 5.2 문자가 지나가는 층

1. 클라이언트: 터미널이 보내는 문자열 인코딩
2. 연결: 현재 MariaDB 세션이 쿼리를 해석하는 문자셋
3. 데이터베이스 기본값: 새 객체가 물려받는 기본 문자셋
4. 테이블·열: 실제 문자열을 저장하는 문자셋

테이블·열이 latin1이면 연결을 utf8mb4로 바꿔도 한국어 저장은 실패할 수 있다.

## 5.3 한글 INSERT 오류의 원인

필기의 오류:

```text
ERROR 1366 (22007): Incorrect string value: '\xEB\x8D\xB0\xEB\xAF\xB8...' for column library.books.title
```

dump의 테이블 정의:

```sql
) ENGINE=InnoDB AUTO_INCREMENT=4
  DEFAULT CHARSET=latin1
  COLLATE=latin1_swedish_ci;
```

이 기록을 보면 UTF-8로 입력된 한글을 latin1 열에 저장하려고 한 것이 주요 원인이다. 연결 문자셋 문제도 함께 확인해야 하지만, 테이블이 latin1인 것은 확실한 문제다.

## 5.4 현재 상태 확인

```sql
SHOW CREATE DATABASE library;
SHOW CREATE TABLE books;
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';
```

특히 다음을 구분한다.

- character_set_client: 클라이언트가 보내는 쿼리
- character_set_connection: 서버가 쿼리를 해석하는 연결
- 테이블의 DEFAULT CHARSET: 저장 공간

## 5.5 새로 만드는 경우

```sql
CREATE DATABASE library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE library;

CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(50),
    published_year INT,
    available BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

## 5.6 이미 만든 객체를 수정하는 경우

데이터베이스 기본값:

```sql
ALTER DATABASE library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

기존 테이블:

```sql
ALTER TABLE books
  CONVERT TO CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

ALTER DATABASE는 앞으로 새로 만드는 객체의 기본값을 바꾸고, ALTER TABLE CONVERT는 기존 테이블 열을 변환한다. 중요한 데이터가 있으면 먼저 백업한다.

현재 접속 설정:

```sql
SET NAMES utf8mb4;
```

또는:

```bash
mariadb --default-character-set=utf8mb4 -u root -p
```

SET NAMES는 현재 연결의 client·connection·result 문자셋을 설정한다. latin1 테이블을 자동으로 utf8mb4로 변환하는 명령은 아니다.

## 5.7 dump 안의 SET NAMES를 오해하지 않기

dump에 다음 문장이 있어도:

```sql
SET NAMES utf8mb4;
```

뒤의 CREATE TABLE이 DEFAULT CHARSET=latin1이면 테이블은 latin1으로 생성될 수 있다. 복원 연결의 문자셋과 테이블 저장 문자셋은 별도로 확인해야 한다.

---

# 6. INSERT와 SELECT

## 6.1 INSERT

```sql
INSERT INTO books
    (title, author, published_year, available)
VALUES
    ('demian', 'herman', 1919, TRUE);
```

문자열은 작은따옴표, 숫자는 보통 따옴표 없이 입력한다. 열 목록을 명시하면 열 순서 변경이나 새 열 추가에 안전하다.

수업 데이터:

```sql
INSERT INTO books (title, author, published_year, available)
VALUES ('demian', 'herman', 1919, TRUE);

INSERT INTO books (title, author, published_year, available)
VALUES ('young prince', 'juiperi', 1943, TRUE);

INSERT INTO books (title, author, published_year, available)
VALUES ('database essential', 'gil dong', 2026, FALSE);
```

여러 행을 한 번에 입력할 수도 있다.

```sql
INSERT INTO books (title, author, published_year, available)
VALUES
  ('demian', 'herman', 1919, TRUE),
  ('young prince', 'juiperi', 1943, TRUE),
  ('database essential', 'gil dong', 2026, FALSE);
```

id를 생략했으므로 AUTO_INCREMENT가 1, 2, 3을 자동 생성했다.

## 6.2 SELECT 기본

```sql
SELECT 열1, 열2
FROM 테이블
WHERE 조건;
```

모든 열:

```sql
SELECT * FROM books;
```

실제 프로그램에서는 필요한 열을 명시하면 결과 구조를 예측하기 쉽다.

```sql
SELECT id, title, available
FROM books;
```

## 6.3 수업 결과

| id | title | author | published_year | available |
|---:|---|---|---:|---:|
| 1 | demian | herman | 1919 | 1 |
| 2 | young prince | juiperi | 1943 | 1 |
| 3 | database essential | gil dong | 2026 | 0 |

한글 demian 입력은 실패했으므로 성공한 영문 데이터만 표에 남아 있다.

---

# 7. 조건 검색·정렬·집계

## 7.1 WHERE와 비교 연산자

```sql
SELECT *
FROM books
WHERE published_year >= 2000;
```

결과는 2026년 행 하나다.

```sql
SELECT *
FROM books
WHERE author = 'gil dong'
  AND available = FALSE;
```

결과는 database essential 하나다.

| 연산자 | 의미 |
|---|---|
| = | 같다 |
| <> 또는 != | 같지 않다 |
| > | 크다 |
| >= | 크거나 같다 |
| < | 작다 |
| <= | 작거나 같다 |

## 7.2 AND와 OR

AND는 모든 조건이 참이어야 하고 OR는 하나라도 참이면 된다.

```sql
SELECT *
FROM books
WHERE author = 'gil dong'
   OR available = TRUE;
```

이 쿼리는 세 행 모두를 반환한다.

| 행 | 저자가 gil dong | available이 TRUE | OR 결과 |
|---:|---:|---:|---:|
| 1 | 아니오 | 예 | 참 |
| 2 | 아니오 | 예 | 참 |
| 3 | 예 | 아니오 | 참 |

AND가 OR보다 먼저 평가되는 우선순위에 의존하지 말고 괄호를 명시한다.

```sql
SELECT *
FROM books
WHERE (author = 'gil dong' OR author = 'herman')
  AND available = TRUE;
```

## 7.3 BETWEEN

```sql
SELECT *
FROM books
WHERE published_year BETWEEN 1900 AND 2000;
```

BETWEEN은 양 끝값을 포함한다. 위 조건은 다음과 같은 의미다.

```sql
WHERE published_year >= 1900
  AND published_year <= 2000
```

결과는 1919와 1943년 행이다.

## 7.4 LIKE

```sql
SELECT *
FROM books
WHERE title LIKE '%data%';
```

퍼센트는 0개 이상의 임의 문자열, 밑줄은 정확히 한 문자를 뜻한다. 콜레이션에 따라 대소문자 구분 여부가 달라질 수 있다.

```sql
SELECT * FROM books WHERE title LIKE 'data%';
SELECT * FROM books WHERE title LIKE '%essential';
SELECT * FROM books WHERE title LIKE 'd_ta';
```

## 7.5 NULL

NULL은 0이나 빈 문자열이 아니라 값이 없거나 알 수 없는 상태다.

잘못된 비교:

```sql
WHERE author = NULL
```

올바른 비교:

```sql
SELECT * FROM books WHERE title IS NULL;
SELECT * FROM books WHERE title IS NOT NULL;
```

title이 NOT NULL로 정의되어 있으므로 title IS NULL은 빈 결과가 되고, 현재 세 행은 모두 IS NOT NULL이다.

## 7.6 ORDER BY

```sql
SELECT *
FROM books
ORDER BY published_year ASC;

SELECT *
FROM books
ORDER BY published_year DESC;
```

ASC는 오름차순, DESC는 내림차순이며 ASC가 기본값이다. ORDER BY가 없으면 결과 순서를 보장한다고 가정하지 않는다.

## 7.7 LIMIT

```sql
SELECT *
FROM books
ORDER BY published_year DESC
LIMIT 1;
```

정렬 후 첫 행 하나를 가져오므로 가장 최신 연도의 책이 나온다. LIMIT만 쓰면 어떤 행이 선택될지 명확하지 않다.

오프셋:

```sql
SELECT *
FROM books
ORDER BY published_year DESC
LIMIT 1 OFFSET 1;
```

## 7.8 오타로 인한 오류

잘못된 열 이름:

```sql
ORDER BY pubished_year DESC
```

실제 열은 published_year이다.

```text
ERROR 1054 (42S22): Unknown column 'pubished_year' in 'order clause'
```

DESC books 또는 SHOW CREATE TABLE books로 실제 식별자를 확인한다.

## 7.9 집계 함수

```sql
SELECT COUNT(*) AS total_books
FROM books;

SELECT SUM(published_year) AS total_year
FROM books;

SELECT AVG(published_year) AS avg_year
FROM books;

SELECT MIN(published_year) AS oldest_year,
       MAX(published_year) AS newest_year
FROM books;
```

수업 결과:

| 함수 | 결과 | 의미 |
|---|---:|---|
| COUNT(*) | 3 | 행 세 개 |
| SUM(published_year) | 5888 | 1919+1943+2026 |
| AVG(published_year) | 1962.6667 | 세 연도의 산술평균 |
| MIN(published_year) | 1919 | 가장 작은 연도 |
| MAX(published_year) | 2026 | 가장 큰 연도 |

COUNT(*)는 행 전체를 세고 COUNT(author)는 author가 NULL이 아닌 행만 센다. SUM·AVG·MIN·MAX는 일반적으로 NULL을 계산에서 제외한다. 5888은 SQL 계산으로는 맞지만 “책의 총 연도”가 업무상 유용한 지표라는 뜻은 아니다.

논리적 처리 순서는 대략 FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT로 이해하면 된다.

---

# 8. 백업과 복원

## 8.1 백업과 복제의 차이

| 구분 | 백업·복원 | 복제 |
|---|---|---|
| 목적 | 특정 시점 보관·복구·이전 | 변경 사항의 지속 전달 |
| 산출물 | SQL dump 또는 물리 백업 | binary log와 replica 상태 |
| 성격 | 일회성 | 지속적 |
| 오류 보호 | 과거 시점으로 복구 가능 | 원본의 실수도 전달될 수 있음 |

복제는 백업을 대신하지 않는다. 원본에서 잘못 실행한 DELETE가 replica에도 적용될 수 있다.

## 8.2 mariadb-dump

현재 공식 명칭:

```bash
mariadb-dump -u root -p library > backup.sql
```

수업에서 사용한 호환 명칭:

```bash
mysqldump -u root -p library > backup.sql
```

u는 사용자, p는 비밀번호 입력, library는 데이터베이스다.

## 8.3 데이터베이스 하나

```bash
umask 077
mariadb-dump -u root -p library > backup.sql
ls -l backup.sql
chmod 600 backup.sql
```

dump는 다음을 포함한다.

- DROP TABLE IF EXISTS
- CREATE TABLE
- INSERT
- SQL 모드와 문자셋 설정

필기의 backup.sql이 world-readable인 rw-r--r-- 상태였다면 다른 사용자가 읽을 수 있다. 실제 데이터가 들어 있는 dump는 600처럼 제한된 권한으로 보관한다.

## 8.4 전체 데이터베이스

```bash
mariadb-dump -u root -p --all-databases > all_backup.sql
chmod 600 all_backup.sql
```

복원:

```bash
mariadb -u root -p < all_backup.sql
```

전체 백업에는 시스템 데이터베이스와 모든 사용자 데이터가 포함될 수 있으므로 복원 전 대상 상태를 확인한다.

## 8.5 특정 테이블

```bash
mariadb-dump -u root -p library books > table_backup.sql
mariadb -u root -p library < table_backup.sql
```

첫 번째 library는 데이터베이스, 두 번째 books는 테이블이다. 이 dump는 library 데이터베이스가 이미 존재해야 한다.

데이터베이스 생성 문장까지 포함하려면:

```bash
mariadb-dump -u root -p --databases library > library_with_create.sql
```

## 8.6 수업에서 한 복원의 정확한 의미

```bash
mariadb -u root -p library < backup.sql
```

이는 library에 접속하여 SQL 파일을 차례로 실행한다는 뜻이다. 같은 서버의 library에서 dump하고 같은 library로 복원했다면 dump·restore 왕복 테스트이지, 다른 서버로의 migration이나 replication 성공 증명은 아니다.

## 8.7 복제용 일관된 dump

기존 데이터가 있는 상태에서 replica를 초기화할 때:

```bash
umask 077
mariadb-dump -u root -p \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --master-data=2 \
  --databases library \
  > /root/library_for_replication.sql
chmod 600 /root/library_for_replication.sql
```

옵션:

| 옵션 | 의미 |
|---|---|
| default-character-set=utf8mb4 | dump 클라이언트의 문자셋 |
| single-transaction | InnoDB 중심에서 일관된 스냅샷을 만들 때 유용 |
| master-data=2 | dump 시점의 binary log 파일·위치를 주석으로 기록 |
| databases library | CREATE DATABASE·USE 문장까지 포함 |

master-data=2가 중요한 이유는 dump 데이터의 시점과 복제를 시작할 위치를 연결하기 때문이다. dump가 끝난 뒤 나중에 본 현재 위치를 무조건 사용하면 dump와 좌표가 어긋날 수 있다.

저장 프로시저·이벤트·트리거까지 필요하면 환경에 따라 routines·events·triggers 옵션도 고려한다.

---

# 9. firewalld와 원격 접속

## 9.1 필요한 네 가지

replica가 primary MariaDB에 접속하려면 모두 충족해야 한다.

1. primary의 MariaDB 서비스 실행
2. primary가 LAN 인터페이스의 TCP 3306 수신
3. firewalld가 3306/TCP 허용
4. 복제 계정의 사용자·Host·비밀번호 일치

## 9.2 수업 명령

```bash
firewall-cmd --permanent --add-port=3306/tcp
firewall-cmd --reload
firewall-cmd --list-all
```

permanent는 영구 설정을 바꾸고 reload는 그 설정을 현재 런타임에 적용한다. permanent만 입력하고 reload하지 않으면 현재 실행 중인 규칙에 바로 반영되지 않을 수 있다.

```bash
firewall-cmd --list-ports
firewall-cmd --permanent --list-ports
firewall-cmd --get-active-zones
```

list-all은 zone의 인터페이스·서비스·포트를 함께 보여 준다.

## 9.3 특정 replica만 허용

실습망에서 전체를 열 수는 있지만, 운영 환경에서는 replica IP만 허용하는 편이 안전하다.

```bash
firewall-cmd --permanent --zone=public \
  --add-rich-rule='rule family="ipv4" source address="<REPLICA_IP>/32" port port="3306" protocol="tcp" accept'
firewall-cmd --reload
```

이미 전체 3306을 열었다면:

```bash
firewall-cmd --permanent --zone=public --remove-port=3306/tcp
firewall-cmd --reload
```

## 9.4 실제 수신 여부

```bash
ss -lntp | grep 3306
```

0.0.0.0:3306 또는 primary LAN IP가 보이면 외부 IPv4 수신이 가능하다. 127.0.0.1:3306만 보이면 외부에서 접속할 수 없다.

MariaDB가 3306을 수신하고 있는지와 firewalld가 허용하는 것은 별개의 문제다.

## 9.5 원격 계정 테스트

replica에서 복제 전에 직접 접속한다.

```bash
mariadb -h <PRIMARY_IP> -P 3306 \
  -u repl -p \
  -e "SELECT 1;"
```

이 테스트가 실패한 상태에서 CHANGE MASTER TO만 반복해도 복제는 성공하지 않는다.

---

# 10. migration과 replication

## 10.1 migration

Migration은 서비스와 데이터를 다른 시스템으로 옮기는 작업이다. 트래픽이 많거나 중단이 어려우면 다음처럼 진행할 수 있다.

1. 원본의 초기 복사본을 만든다.
2. 새 서버에 복원한다.
3. 원본의 이후 변경을 새 서버가 따라가게 한다.
4. 차이가 작아지면 트래픽을 새 서버로 전환한다.

2번은 백업·복원이고 3번은 replication이다.

## 10.2 replication

현재 문서 용어:

- primary: 변경을 실행하고 binary log를 기록하는 원본
- replica: binary log를 받아 적용하는 대상

수업의 master는 primary, slave는 replica에 해당한다. MariaDB 문서에는 legacy 명령과 새 명칭이 함께 존재한다.

복제 흐름:

```mermaid
flowchart LR
    P["Primary<br/>변경 실행"] --> B["Binary log<br/>이벤트 기록"]
    B --> I["Replica I/O thread<br/>relay log 기록"]
    I --> S["Replica SQL thread<br/>변경 적용"]
```

replica는 원본 데이터 파일을 공유하는 것이 아니라, 원본의 변경 이벤트를 받아 자기 서버에서 실행한다.

## 10.3 비동기·반동기·동기

| 방식 | 커밋 시 대상 확인 | 장점 | 대가 |
|---|---|---|---|
| 비동기 | 기다리지 않음 | 지연 작음·구성 단순 | 장애 시 전달 전 최근 변경 유실 가능 |
| 반동기 | 최소 한 replica의 수신 확인을 기다리는 방식 | 유실 위험 감소 | 네트워크·replica 상태가 지연에 영향 |
| 동기 | 대상 적용까지 더 강하게 맞추는 개념 | 일관성 강화 | 지연·가용성 비용 증가 |

이번 실습은 MariaDB 표준 비동기 replication이다. semisync나 Galera 동기 클러스터를 설정한 것이 아니다.

## 10.4 여러 replica와 백업

하나의 primary에 여러 replica를 둘 수 있지만 표준 replication이 자동으로 쓰기를 분산해 주는 것은 아니다. 또한 replica에도 원본의 DELETE·오류가 전달될 수 있으므로 별도의 시점별 backup이 필요하다.

## 10.5 과거 데이터는 자동 backfill되지 않는다

replica가 시작한 binary log 좌표 이후의 이벤트만 적용된다. primary에 이미 존재하지만 replica에 없는 library를 초기 dump 없이 복제만 시작하면 과거의 CREATE DATABASE와 INSERT가 자동으로 채워지지 않는다.

---

# 11. binary log와 복제 설정값

## 11.1 binary log

binary log는 데이터 파일 복사본이 아니라 데이터·구조 변경 이벤트를 기록하는 로그다.

```sql
SHOW VARIABLES LIKE 'log_bin';
SHOW BINARY LOGS;
SHOW MASTER STATUS;
```

SHOW MASTER STATUS는 현재 접속한 서버의 binary log 상태다. replica 설정에 사용할 파일·위치는 반드시 primary에서 확인해야 한다.

## 11.2 primary 설정 파일

수업 파일:

```bash
vi /etc/my.cnf.d/mariadb-server.cnf
```

예시:

```ini
[mysqld]
server-id=1
log_bin=/var/log/mysql/mysql-bin
binlog_format=ROW
sync_binlog=1
expire_logs_days=10
max_binlog_size=100M
```

## 11.3 설정값

### server-id

복제 토폴로지에서 서버를 구별하는 숫자다. primary와 모든 replica가 서로 달라야 한다.

```sql
SHOW VARIABLES LIKE 'server_id';
```

필기의 show variable like는 잘못된 표현이며 VARIABLES 복수형을 사용한다.

### log_bin

binary log를 켜고 파일 basename 또는 경로를 지정한다. 위 설정이면 mysql-bin.000001, mysql-bin.000002처럼 번호가 붙을 수 있다.

### expire_logs_days

binary log 보존 기간을 일 단위로 지정한다. replica가 아직 읽지 않은 로그가 삭제되면 복제가 끊길 수 있으므로 무조건 10일이 안전하다는 뜻은 아니다. 최신 문서에는 binlog_expire_logs_seconds도 있다.

### max_binlog_size

binary log 파일 회전의 대략적인 기준이다. 하나의 큰 트랜잭션을 이 값보다 작게 자동 분할하는 한계값은 아니다.

### binlog_format

| 형식 | 특징 |
|---|---|
| STATEMENT | SQL 문장 중심, 비결정적 문장에서 주의 |
| ROW | 행 변경 중심, 결과 예측이 쉽지만 로그가 커질 수 있음 |
| MIXED | 상황에 따라 혼합 |

기본값은 버전과 설정에 따라 다를 수 있으므로 확인한다.

```sql
SHOW VARIABLES LIKE 'binlog_format';
```

### sync_binlog

binary log를 디스크에 동기화하는 빈도와 관련된다. 0은 운영체제 flush에 의존하고 1은 커밋마다 디스크 동기화를 강화하는 방향이며, 큰 값은 성능과 내구성을 절충한다.

```sql
SHOW VARIABLES LIKE 'sync_binlog';
```

## 11.4 binary log 디렉터리 권한

필기의 chmod 777:

```bash
mkdir /var/log/mysql
chmod 777 /var/log/mysql
```

동작할 수는 있지만 누구나 읽고 쓸 수 있는 과도한 권한이다. MariaDB 프로세스가 접근하도록 최소 권한을 사용한다.

```bash
install -d -o mysql -g mysql -m 750 /var/log/mysql
```

재시작에 실패하면:

```bash
systemctl status mariadb
journalctl -u mariadb -n 100 --no-pager
ls -ld /var/log/mysql
```

## 11.5 replica 설정

```ini
[mysqld]
server-id=2
```

선택적으로 직접 쓰기를 줄이기 위해:

```ini
read_only=ON
```

read_only는 관리자와 replication thread까지 모두 막는 절대적인 보안 장치가 아니다. 단일 primary·replica에서 replica 자체가 downstream source가 되지 않는다면 replica의 log_bin은 필수는 아니다. cascading replication에는 필요할 수 있다.

---

# 12. 표준 복제 실습의 올바른 순서

주소와 좌표는 기록을 외워 쓰지 말고 현재 화면에서 확인한다.

- PRIMARY_IP: binary log를 기록하는 원본 IP
- REPLICA_IP: 원본을 따라가는 대상 IP
- REPL_PASSWORD: 복제 계정 비밀번호

필기에는 192.168.16.131과 192.168.16.21이 모두 MASTER_HOST로 등장한다. 같은 실습에서 둘을 동시에 쓸 수 없으므로 실제 primary에서 다음을 실행하여 하나를 확정한다.

```bash
hostname
ip -br address
hostname -I
```

## 12.1 primary 준비

```bash
systemctl enable --now mariadb
install -d -o mysql -g mysql -m 750 /var/log/mysql
vi /etc/my.cnf.d/mariadb-server.cnf
systemctl restart mariadb
```

설정:

```ini
[mysqld]
server-id=1
log_bin=/var/log/mysql/mysql-bin
binlog_format=ROW
expire_logs_days=10
max_binlog_size=100M
```

확인:

```sql
SHOW VARIABLES LIKE 'server_id';
SHOW VARIABLES LIKE 'log_bin';
SHOW VARIABLES LIKE 'binlog_format';
SHOW MASTER STATUS;
```

SHOW MASTER STATUS가 비어 있으면 binary log가 켜지지 않았거나 현재 서버가 기대한 primary가 아닐 수 있다.

## 12.2 복제 계정

가능하면 replica IP를 제한한다.

```sql
CREATE USER 'repl'@'<REPLICA_IP>'
  IDENTIFIED BY '<REPL_PASSWORD>';

GRANT REPLICATION SLAVE
  ON *.*
  TO 'repl'@'<REPLICA_IP>';
```

수업 형태:

```sql
GRANT REPLICATION SLAVE
  ON *.*
  TO 'slave_db'@'%'
  IDENTIFIED BY 'slave_password';
```

퍼센트는 Host 부분의 와일드카드다. 외부 접속을 자동으로 여는 것은 아니지만, 네트워크와 비밀번호가 허용되면 여러 출발지에서 매칭될 수 있어 운영 환경에는 넓은 권한이다.

GRANT와 CREATE USER는 즉시 반영되므로 보통 FLUSH PRIVILEGES가 필수는 아니다.

## 12.3 방화벽과 원격 계정 확인

primary:

```bash
firewall-cmd --permanent --zone=public --add-port=3306/tcp
firewall-cmd --reload
ss -lntp | grep 3306
```

replica:

```bash
mariadb -h <PRIMARY_IP> -P 3306 -u repl -p -e "SELECT 1;"
```

이 직접 접속이 먼저 성공해야 한다.

## 12.4 방법 A: 기존 데이터가 없는 새 변경 테스트

### primary에서 현재 좌표 확인

```sql
SHOW MASTER STATUS;
```

예시:

```text
File: mysql-bin.000001
Position: 328
```

이 숫자는 예시다. 실제 값으로 바꾼다.

### replica server-id 설정

```bash
vi /etc/my.cnf.d/mariadb-server.cnf
systemctl restart mariadb
```

```ini
[mysqld]
server-id=2
```

확인:

```sql
SHOW VARIABLES LIKE 'server_id';
```

### replica 연결 설정

수업 환경에서 사용하는 명령:

```sql
CHANGE MASTER TO
  MASTER_HOST='<PRIMARY_IP>',
  MASTER_USER='repl',
  MASTER_PASSWORD='<REPL_PASSWORD>',
  MASTER_PORT=3306,
  MASTER_LOG_FILE='mysql-bin.000001',
  MASTER_LOG_POS=328;
```

파일과 위치는 primary에서 확인한 실제 값으로 바꾼다.

### replica 시작

```sql
START SLAVE;
```

중지·초기화는 별도 명령이다.

```sql
STOP SLAVE;
RESET SLAVE ALL;
```

최신 MariaDB 문서에서는 START REPLICA·STOP REPLICA·SHOW REPLICA STATUS 명칭도 사용한다. 수업 버전에서는 START SLAVE·SHOW SLAVE STATUS를 우선 사용한다.

### primary에서만 새 변경

```sql
CREATE DATABASE repl_test
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE repl_test;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

INSERT INTO users (name) VALUES ('hong');
INSERT INTO users (name) VALUES ('lee');
```

### replica에서 확인

```sql
SHOW DATABASES;
USE repl_test;
SELECT * FROM users ORDER BY id;
```

replica에서 직접 CREATE DATABASE나 INSERT를 실행하면 복제 검증이 아니다.

## 12.5 방법 B: 기존 library 초기 복사

primary에 이미 library가 있고 replica에는 없을 때:

### primary에서 dump

```bash
umask 077
mariadb-dump -u root -p \
  --default-character-set=utf8mb4 \
  --single-transaction \
  --master-data=2 \
  --databases library \
  > /root/library_for_replication.sql
chmod 600 /root/library_for_replication.sql
grep -n -i "CHANGE MASTER" /root/library_for_replication.sql
```

### replica로 복사·복원

```bash
scp /root/library_for_replication.sql root@<REPLICA_IP>:/root/
mariadb -u root -p < /root/library_for_replication.sql
```

실제 작업에서는 복제 연결 상태와 대상 데이터가 실습용인지 먼저 확인한다.

### dump에 기록된 좌표 사용

dump 안의 주석 예:

```text
-- CHANGE MASTER TO MASTER_LOG_FILE='mysql-bin.000001', MASTER_LOG_POS=328;
```

필기의 mysql-bin.000002 / 342, mysql-bin.000001 / 328, mysql-bin.000001 / 1105를 서로 섞어 쓰면 안 된다. 같은 snapshot에 대응하는 파일·위치 쌍을 사용한다.

### replica에서 연결

```sql
CHANGE MASTER TO
  MASTER_HOST='<PRIMARY_IP>',
  MASTER_USER='repl',
  MASTER_PASSWORD='<REPL_PASSWORD>',
  MASTER_PORT=3306,
  MASTER_LOG_FILE='<FILE_FROM_DUMP>',
  MASTER_LOG_POS=<POSITION_FROM_DUMP>;

START SLAVE;
SHOW SLAVE STATUS;
```

---

# 13. 복제 상태 확인과 성공 판정

## 13.1 상태 명령

replica에서:

```sql
SHOW SLAVE STATUS;
```

가로 출력이 길면:

```sql
SHOW SLAVE STATUS\G
```

최신 문서 명칭:

```sql
SHOW REPLICA STATUS\G
```

## 13.2 핵심 필드

| 필드 | 정상 기대값 | 의미 |
|---|---|---|
| Master_Host | 실제 primary IP | 연결 대상 |
| Master_Port | 3306 | TCP 포트 |
| Slave_IO_Running | Yes | primary binary log를 읽는 thread 실행 |
| Slave_SQL_Running | Yes | relay log를 적용하는 thread 실행 |
| Last_IO_Error | 비어 있음 | I/O 연결 오류 없음 |
| Last_SQL_Error | 비어 있음 | SQL 적용 오류 없음 |
| Seconds_Behind_Master | 0 또는 작은 값 | 지연 추정치 |

Seconds_Behind_Master만 0이라고 성공을 확정하지 않는다. 두 thread가 모두 Yes이고 오류가 없으며 primary에서만 만든 테스트 행이 replica에 있어야 한다.

## 13.3 원문에서 성공을 확정할 수 없는 이유

원문에는 SHOW SLAVE STATUS 명령은 있지만 결과 필드가 없다. replica에서 information_schema·mysql·performance_schema만 보였고, 이후 replitest를 대상 서버에서 직접 CREATE DATABASE했다. 이 기록만으로는 replication 성공의 증거가 없다.

## 13.4 SHOW MASTER STATUS의 위치

현재 서버의 상태를 보여 준다.

- primary에서 실행: replica가 읽어야 할 source 좌표
- replica에서 실행: replica 자신의 binary log 좌표일 수 있음

replica에서 나온 좌표를 primary 좌표로 착각하지 않는다.

## 13.5 검증 시나리오

primary에서만:

```sql
CREATE DATABASE repl_verify
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE repl_verify;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

INSERT INTO users (name) VALUES ('hong');
INSERT INTO users (name) VALUES ('lee');
```

replica에서:

```sql
SHOW SLAVE STATUS\G
SHOW DATABASES;
USE repl_verify;
SELECT * FROM users ORDER BY id;
```

기대 행:

| id | name |
|---:|---|
| 1 | hong |
| 2 | lee |

---

# 14. 필기 오류·누락·혼동 정리

| 필기 기록 | 정확한 해석 |
|---|---|
| AUTO_INCREAMENT | AUTO_INCREMENT |
| Incorrect string value | 테이블 dump가 latin1이므로 utf8mb4 저장이 필요. 연결 문자셋도 확인 |
| show variable like server_id | SHOW VARIABLES LIKE 'server_id' |
| pubished_year | published_year |
| MASTER_HOST 192.168.16.131와 192.168.16.21 | 실제 primary IP를 확인하여 하나만 사용 |
| binlog 000002/342와 000001/328 | 같은 snapshot의 파일·위치 쌍만 사용 |
| 000001/1105 | 다른 시점의 좌표일 수 있으므로 앞 dump와 임의로 조합하지 않음 |
| slave_db@% | Host 와일드카드. 실습 외에는 replica IP 제한 |
| FLUSH PRIVILEGES 필수 | GRANT·CREATE USER 후 일반적으로 필수 아님 |
| chmod 777 | 동작은 가능하나 과도한 권한. mysql 소유와 최소 권한 사용 |
| replica에서 SHOW MASTER STATUS | 자기 binary log일 수 있음. 연결 좌표는 primary에서 가져옴 |
| replica에 library가 없음 | 초기 dump 복원이 빠졌거나 과거 데이터가 자동 backfill되지 않은 상태 가능 |
| replica에서 replitest 생성 | 직접 생성한 것이므로 복제 검증이 아님 |
| start(stop/reset) slave | START, STOP, RESET은 각각 다른 명령 |
| dump 후 같은 DB로 restore | 왕복 테스트이지 migration·replication 성공 증명 아님 |
| dump의 SET NAMES utf8mb4 | 연결 문자셋이지 테이블 latin1을 자동 변경하지 않음 |

## 가장 중요한 세 가지 구분

### 계정과 방화벽

slave_db@%는 MariaDB 내부 계정의 Host 조건이고 3306 허용은 운영체제 방화벽 규칙이다. 둘은 서로 다른 층이며 둘 다 맞아야 한다.

### dump와 binary log

dump는 특정 시점의 구조·데이터이고 binary log는 그 이후의 변경 이벤트다. 초기 dump와 그 시점의 좌표가 연결되어야 replica가 빠진 변경 없이 이어진다.

### 명령 입력과 성공 판정

CHANGE MASTER TO와 START SLAVE를 입력한 것만으로 성공이 아니다. status에서 I/O·SQL thread와 오류 필드를 확인하고 primary에서만 만든 행을 replica에서 확인해야 한다.

---

# 15. 오류 진단 순서

문제 발생 시 SQL 문법 → 데이터 구조 → 문자셋 → 서비스·포트 → 계정 → replication 상태 순서로 확인한다.

## 15.1 서버 확인

```bash
hostname
ip -br address
```

```sql
SELECT @@hostname, @@server_id, DATABASE();
```

## 15.2 서비스 확인

```bash
systemctl is-active mariadb
systemctl status mariadb
journalctl -u mariadb -n 100 --no-pager
```

## 15.3 구조 확인

```sql
SHOW DATABASES;
USE library;
SHOW TABLES;
DESC books;
SHOW CREATE TABLE books;
```

### Unknown database

DB가 없는데 USE를 먼저 실행한 경우:

```sql
CREATE DATABASE replitest;
USE replitest;
```

단, replica 검증 중에는 primary에서 먼저 생성했는지 확인한다.

### Table doesn't exist

데이터베이스만 만들고 테이블을 만들지 않은 경우:

```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);
```

### Unknown column

DESC로 실제 열 이름을 확인한다. pubished_year는 오타다.

## 15.4 문자셋 확인

```sql
SHOW VARIABLES LIKE 'character_set%';
SHOW CREATE TABLE books;
```

테이블을 utf8mb4로 변환하고 새 세션에서 SET NAMES 또는 default-character-set 옵션을 적용한다.

## 15.5 원격 3306 확인

primary:

```bash
ss -lntp | grep 3306
firewall-cmd --get-active-zones
firewall-cmd --list-all
```

replica:

```bash
mariadb -h <PRIMARY_IP> -P 3306 -u repl -p -e "SELECT 1;"
```

## 15.6 replication 상태 확인

```sql
SHOW SLAVE STATUS\G
```

### 상태가 빈 결과

- CHANGE MASTER TO가 실행되지 않음
- 다른 connection을 확인함
- RESET SLAVE ALL로 연결 정보가 지워짐
- 현재 서버가 replica가 아님

### Slave_IO_Running이 Connecting 또는 No

Last_IO_Error를 본다.

- Access denied: 사용자·비밀번호·Host 권한
- Can't connect: IP·포트·firewalld·bind-address·서비스
- Could not find first log file: primary 로그가 삭제되었거나 좌표가 잘못됨

### Slave_SQL_Running이 No

Last_SQL_Error를 본다. 초기 dump와 replica 데이터가 불일치하거나 좌표가 잘못되었거나 replica에 직접 데이터를 만들어 중복이 생긴 경우가 많다. 원인 확인 없이 SQL_SLAVE_SKIP_COUNTER로 건너뛰면 데이터가 더 불일치할 수 있다.

재설정이 필요할 때:

```sql
STOP SLAVE;
RESET SLAVE ALL;
```

RESET SLAVE ALL은 relay log와 복제 메타데이터를 초기화한다. primary의 데이터베이스를 지우는 명령은 아니지만 replica의 진행 상태를 잃으므로 실습용 대상인지 확인한다.

---

# 16. 최종 체크리스트와 공식 자료

## 16.1 SQL

```sql
CREATE DATABASE library
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE library;

CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    author VARCHAR(50),
    published_year INT,
    available BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

INSERT INTO books (title, author, published_year, available)
VALUES ('데미안', '헤르만 헤세', 1919, TRUE);

SELECT * FROM books;
SELECT * FROM books WHERE published_year >= 2000;
SELECT * FROM books WHERE published_year BETWEEN 1900 AND 2000;
SELECT * FROM books WHERE title LIKE '%data%';
SELECT * FROM books WHERE title IS NOT NULL;
SELECT * FROM books ORDER BY published_year DESC LIMIT 1;
```

## 16.2 백업

```bash
umask 077
mariadb-dump -u root -p library > backup.sql
chmod 600 backup.sql
mariadb-dump -u root -p --all-databases > all_backup.sql
mariadb-dump -u root -p library books > table_backup.sql
mariadb -u root -p library < backup.sql
```

## 16.3 primary

```ini
[mysqld]
server-id=1
log_bin=/var/log/mysql/mysql-bin
binlog_format=ROW
expire_logs_days=10
max_binlog_size=100M
```

```sql
SHOW VARIABLES LIKE 'server_id';
SHOW VARIABLES LIKE 'log_bin';
SHOW MASTER STATUS;
CREATE USER 'repl'@'<REPLICA_IP>' IDENTIFIED BY '<REPL_PASSWORD>';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'<REPLICA_IP>';
```

## 16.4 replica

```ini
[mysqld]
server-id=2
```

```sql
CHANGE MASTER TO
  MASTER_HOST='<PRIMARY_IP>',
  MASTER_USER='repl',
  MASTER_PASSWORD='<REPL_PASSWORD>',
  MASTER_PORT=3306,
  MASTER_LOG_FILE='<FILE_FROM_PRIMARY_OR_DUMP>',
  MASTER_LOG_POS=<POSITION_FROM_PRIMARY_OR_DUMP>;

START SLAVE;
SHOW SLAVE STATUS\G
```

## 16.5 성공 판정

- Master_Host가 실제 primary IP다.
- Slave_IO_Running이 Yes다.
- Slave_SQL_Running이 Yes다.
- Last_IO_Error와 Last_SQL_Error가 비어 있다.
- primary에서만 만든 DB·테이블·행이 replica에서 조회된다.

## 16.6 공식 자료

최신 공식 문서는 2026-08-27에 확인했다. 문서의 최신 용어와 MariaDB 10.5.29의 legacy 명령을 함께 비교한다.

### SQL·문자셋

- [CREATE DATABASE](https://mariadb.com/docs/server/reference/sql-statements/data-definition/create/create-database)
- [CREATE TABLE](https://mariadb.com/docs/server/server-usage/tables/create-table)
- [Setting Character Sets and Collations](https://mariadb.com/docs/server/reference/data-types/string-data-types/character-sets/setting-character-sets-and-collations)
- [SET NAMES](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/set-commands/set-names)
- [BOOLEAN](https://mariadb.com/docs/server/reference/data-types/numeric-data-types/boolean)
- [LIKE](https://mariadb.com/docs/server/reference/sql-functions/string-functions/like)
- [BETWEEN AND](https://mariadb.com/docs/server/reference/sql-structure/operators/comparison-operators/between-and)
- [IS NULL](https://mariadb.com/docs/server/reference/sql-structure/operators/comparison-operators/is-null)
- [Operator Precedence](https://mariadb.com/docs/server/reference/sql-structure/operators/operator-precedence)
- [SELECT](https://mariadb.com/docs/server/reference/sql-statements/data-manipulation/selecting-data/select)
- [ORDER BY](https://mariadb.com/docs/server/reference/sql-statements/data-manipulation/selecting-data/order-by)
- [LIMIT](https://mariadb.com/docs/server/reference/sql-statements/data-manipulation/selecting-data/limit)
- [Aggregate Functions](https://mariadb.com/docs/server/reference/sql-functions/aggregate-functions)

### 백업·복원

- [mariadb-dump](https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump)
- [Making Backups with mariadb-dump](https://mariadb.com/docs/server/mariadb-quickstart-guides/mariadb-backup-guide)
- [Restoring Data from Dump Files](https://mariadb.com/docs/server/mariadb-quickstart-guides/mariadb-restore-guide)
- [Backup and Restore Overview](https://mariadb.com/docs/server/server-usage/backup-and-restore/backup-and-restore-overview)
- [Full Backup and Restore with mariadb-backup](https://mariadb.com/docs/server/server-usage/backup-and-restore/mariadb-backup/full-backup-and-restore-with-mariadb-backup)

### 복제·binary log

- [Replication](https://mariadb.com/docs/server/ha-and-performance/standard-replication)
- [Setting Up Replication](https://mariadb.com/docs/server/ha-and-performance/standard-replication/setting-up-replication)
- [CHANGE MASTER TO](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/replication-statements/change-master-to)
- [START REPLICA](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/replication-statements/start-replica)
- [SHOW REPLICA STATUS](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/show/show-replica-status)
- [Legacy Replication Statements](https://mariadb.com/docs/server/reference/sql-statements/administrative-sql-statements/replication-statements/legacy-replication-statements)
- [Replication and Binary Log System Variables](https://mariadb.com/docs/server/ha-and-performance/standard-replication/replication-and-binary-log-system-variables)
- [Activating the Binary Log](https://mariadb.com/docs/server/server-management/server-monitoring-logs/binary-log/activating-the-binary-log)
- [Binary Log Formats](https://mariadb.com/docs/server/server-management/server-monitoring-logs/binary-log/binary-log-formats)
- [Semisynchronous Replication](https://mariadb.com/docs/server/ha-and-performance/standard-replication/semisynchronous-replication)
- [Global Transaction ID](https://mariadb.com/docs/server/ha-and-performance/standard-replication/gtid)

### firewalld

- [Open a Port or Service](https://firewalld.org/documentation/howto/open-a-port-or-service.html)
- [firewall-cmd Manual Page](https://firewalld.org/documentation/man-pages/firewall-cmd.html)
- [Using and Configuring firewalld on RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/configuring_firewalls_and_packet_filters/using-and-configuring-firewalld_firewall-packet-filters)

---

## 한 문장 최종 정리

utf8mb4로 올바른 테이블을 만들고 SQL로 데이터를 다룬 뒤, 일관된 dump로 replica를 초기화하고, primary의 binary log 좌표를 사용해 CHANGE MASTER TO를 구성하여 I/O thread·SQL thread와 실제 데이터 반영을 모두 확인하는 것이 이번 수업의 핵심이다.
