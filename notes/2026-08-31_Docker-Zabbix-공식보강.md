# 2026-08-31 수업 보강 · Docker·Zabbix 공식 문서 대조

> 원문 필기에서 Docker 실습과 Ubuntu 24.04 기반 Zabbix 설치 부분을 추려서, 2026년 8월 기준 공식 문서와 대조한 보강 노트다.
>
> 수업의 기준 버전은 **Ubuntu 24.04 + Zabbix 7.0**으로 유지한다. 공식 매뉴얼의 최신 버전과 수업 버전이 다를 수 있으므로, 실습 명령은 반드시 선택한 Zabbix 버전에 맞춰 확인한다.

## 먼저 바로잡아야 할 내용

| 필기의 표현 | 정확한 정리 |
|---|---|
| Kubernetes(K8s) = Docker | 둘은 같은 제품이 아니다. Docker는 이미지·컨테이너를 다루는 엔진/도구이고, Kubernetes는 여러 노드의 컨테이너를 배치·복구·확장하는 오케스트레이터다. Docker로 만든 이미지는 Kubernetes에서 사용할 수 있지만, Kubernetes와 Docker를 등식으로 쓰면 안 된다. |
| 태그를 생략하면 latest(최신 버전) | 태그를 생략하면 기본 태그가 latest가 될 뿐이다. latest가 가장 최신 빌드라는 보장은 없고, 태그가 이동할 수도 있다. 재현 가능한 실습·배포는 버전 태그나 digest를 고정한다. |
| Ubuntu에서 패키지가 없으면 EPEL 설치 | EPEL은 Enterprise Linux 계열용 저장소다. Ubuntu에서는 Ubuntu 공식 저장소, 공급자 공식 저장소, 검증된 deb 패키지 또는 소스 빌드를 선택한다. |
| PHP 8.3 이상이면 PHP-FPM이 무조건 필요 | Zabbix 프론트엔드의 웹 서버·PHP 연동 방식에 따라 필요한 패키지가 달라진다. PHP-FPM은 Apache/Nginx 구성에서 사용할 수 있는 방식이지 PHP 버전만으로 결정되는 규칙이 아니다. |
| Zabbix Server Name = agent Hostname | 웹 설치 화면의 Server name은 화면에 표시하는 이름이다. 에이전트의 Hostname은 호스트 등록 정보와 active check를 매칭하는 식별자다. 실습에서는 이해를 위해 같게 적을 수 있지만 의미는 다르다. |
| DB 사용자에게 WITH GRANT OPTION 부여 | Zabbix가 자기 데이터베이스를 운영하는 데 다른 사용자에게 권한을 위임할 필요가 없다. 최소 권한 원칙에 따라 해당 DB에만 권한을 준다. |
| 서버·에이전트 포트를 모두 열기 | passive check는 서버에서 에이전트의 10050/tcp로 들어가고, active check는 에이전트가 서버의 10051/tcp로 나간다. 사용하는 방식에 필요한 방향만 허용한다. |

## 1. Docker 개념을 실습 결과와 연결하기

### 1-1. 이미지·컨테이너·호스트

- **이미지**는 컨테이너를 만들기 위한 읽기 전용 레이어 기반 패키지다.
- **컨테이너**는 이미지에서 만들어져 실행되는 프로세스 단위다. 컨테이너마다 별도의 전체 커널을 부팅하는 가상머신과 다르게, 일반적인 Linux 컨테이너는 호스트 커널을 공유한다.
- 컨테이너에는 이미지 위에 쓰기 가능한 레이어가 생긴다. 컨테이너를 삭제하면 그 레이어의 데이터도 사라질 수 있으므로, 보존할 데이터는 volume이나 bind mount에 둔다.
- Docker Hub는 Docker 명령 자체가 아니라 공개 이미지 레지스트리의 한 예다. 사설 레지스트리도 사용할 수 있다.

### 1-2. 필기에서 실행한 명령의 정확한 의미

| 명령 | 의미 |
|---|---|
| **docker image ls** 또는 **docker images** | 로컬 이미지 목록 |
| **docker pull IMAGE** | 레지스트리에서 이미지를 내려받음 |
| **docker run IMAGE COMMAND** | 새 컨테이너를 만들고 시작함. 로컬에 이미지가 없으면 기본 레지스트리에서 pull을 시도함 |
| **docker ps** | 실행 중인 컨테이너만 표시 |
| **docker ps -a** | 실행 중지 상태까지 모든 컨테이너 표시 |
| **docker stop NAME** | 컨테이너 프로세스에 정상 종료를 요청 |
| **docker rm NAME** | 컨테이너를 삭제. 이미지 삭제와는 다름 |
| **docker rmi IMAGE** | 로컬 이미지의 태그·레이어를 삭제. 해당 이미지를 참조하는 컨테이너가 있으면 실패할 수 있음 |
| **docker exec -it NAME bash** | 실행 중인 컨테이너 안에서 추가 명령을 실행 |
| **docker logs NAME** | 컨테이너의 표준 출력·오류 로그 확인 |

**docker run -it ubuntu:bionic bash**의 옵션은 다음처럼 읽는다.

- **-i**: 표준 입력을 열어 둔다.
- **-t**: 터미널을 할당한다.
- **ubuntu:bionic**: 이미지 이름과 태그다.
- **bash**: 컨테이너가 시작할 때 실행할 명령이다. 이 프로세스가 종료되면 컨테이너도 종료된다.

일회성 테스트라면 다음처럼 자동 삭제 옵션을 사용할 수 있다.

~~~bash
docker run --rm -it ubuntu:24.04 bash
~~~

### 1-3. latest와 버전 고정

태그를 생략한 다음 명령은 내부적으로 ubuntu:latest를 가리킨다.

~~~bash
docker pull ubuntu
~~~

하지만 latest는 “항상 가장 최신인 불변 버전”이 아니다. 같은 태그가 다른 이미지 digest를 가리킬 수 있으므로, 수업 결과를 다시 재현할 때는 다음처럼 버전을 명시한다.

~~~bash
docker pull ubuntu:24.04
docker run --rm -it ubuntu:24.04 bash
~~~

운영 배포나 장기 실습에서는 버전 태그보다 digest까지 고정하는 방식이 더 재현성이 높다. 이미지 출처와 digest도 함께 기록한다.

### 1-4. 컨테이너 안에서 apt install이 실패한 이유

필기에서 컨테이너 안에서 바로 git을 설치했을 때 다음 오류가 났다.

~~~text
E: Unable to locate package git
~~~

대개 패키지 자체가 존재하지 않는다는 뜻이 아니라, 이미지 안의 APT 패키지 인덱스가 없거나 오래되었다는 뜻이다. 먼저 인덱스를 갱신한 다음 설치한다.

~~~bash
apt-get update
apt-get install -y git
git --version
cat /etc/os-release
~~~

Dockerfile에서는 APT 인덱스와 설치를 한 레이어에서 처리하고 인덱스 캐시를 지우는 패턴이 일반적이다.

~~~dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
~~~

필기의 ubuntu:bionic은 Ubuntu 18.04 기반의 **레거시 실습 이미지**다. Ubuntu 공식 릴리스 목록상 18.04의 일반 지원은 종료되었으므로, 새 실습은 ubuntu:24.04처럼 지원되는 버전을 우선한다. 기존 실습에서 bionic을 재현해야 한다면 외부에 노출하지 않고, 오래된 저장소·패키지 호환성 문제를 별도로 감안한다.

### 1-5. 데이터 보존과 포트

컨테이너 안에서 생성한 파일을 컨테이너 삭제 뒤에도 보존해야 하면 volume을 사용한다.

~~~bash
docker volume create lab-data
docker run --rm -it --mount source=lab-data,target=/data ubuntu:24.04 bash
~~~

호스트에서 직접 파일을 편집해야 하는 개발 작업은 bind mount를 사용할 수 있다. 컨테이너의 웹 서비스를 호스트 포트로 연결할 때는 명시적으로 매핑한다.

~~~bash
docker run -d --name web -p 8080:80 nginx:stable
docker ps
docker logs web
~~~

**-p 8080:80**은 호스트의 8080번 포트를 컨테이너의 80번 포트로 연결한다. 컨테이너 안에서 80번 포트를 연 것만으로 호스트나 외부에서 자동 접근할 수 있는 것은 아니다.

### 1-6. sudo docker의 의미

Ubuntu 호스트에서 **sudo docker**를 사용한 것은 Docker 데몬과 통신할 권한이 필요했기 때문이다. Docker 소켓에 접근할 수 있는 권한은 사실상 호스트에서 높은 권한을 행사할 수 있는 권한이므로, 실습 계정에 docker 그룹 권한을 부여할 때도 보안 영향을 이해해야 한다.

호스트의 **git 2.43**과 컨테이너 안의 **git 2.17**이 달랐던 것은 서로 다른 사용자 공간 패키지 집합을 사용했기 때문이다. 컨테이너가 호스트 커널을 공유한다는 사실과 컨테이너 사용자 공간이 호스트와 같다는 것은 다른 의미다.

## 2. Linux 패키지 저장소 정리

### 2-1. apt와 apt-get

- **apt update**는 저장소에서 패키지 목록을 새로 받아오는 작업이다. 운영체제 전체를 업그레이드하는 명령이 아니다.
- **apt install**은 패키지와 의존성을 설치한다.
- **apt**는 사람이 터미널에서 사용하기 편한 인터페이스이고, **apt-get**은 스크립트에서 동작이 안정적으로 예측되는 전통적인 도구다. 둘 중 하나가 폐기된 관계는 아니다.
- Ubuntu 24.04에서는 deb822 형식의 **ubuntu.sources** 파일을 사용할 수 있다. 저장소 위치를 설명할 때 특정 한 파일만 있다고 단정하지 말고 실제 설정을 확인한다.

~~~bash
apt-config dump
grep -R --no-filename -E '^(Types|URIs|Suites|Components):' /etc/apt/sources.list.d /etc/apt/sources.list 2>/dev/null
~~~

### 2-2. EPEL과 Ubuntu의 차이

| 운영체제 계열 | 일반적인 패키지 저장소 |
|---|---|
| Ubuntu/Debian | Ubuntu/Debian 공식 저장소, 공급자 공식 저장소, 검증된 deb |
| Rocky/RHEL/Fedora | dnf와 배포판 저장소, RHEL 계열에서 EPEL을 추가 선택 |
| 컨테이너 이미지 | 해당 이미지가 선언한 배포판 저장소 |

외부 저장소나 deb 파일을 추가할 때는 GPG 서명·공식 배포 경로·지원 버전을 확인한다. 단순히 wget으로 파일을 받아 설치하는 것만으로 신뢰성이 확보되지는 않는다.

### 2-3. wget과 curl의 차이

- **wget URL**은 파일을 내려받아 현재 디렉터리에 저장하는 용도에 편하다.
- **curl URL**은 응답을 표준 출력으로 보여 주는 도구다.
- **curl -fsSL URL**에서 f는 HTTP 오류를 실패로 처리하고, s는 조용히 실행하며, S는 조용한 모드에서도 오류를 표시하고, L은 리다이렉트를 따른다. wget과 완전히 같은 명령이라는 뜻은 아니다.

## 3. Ubuntu 24.04에서 Zabbix 7.0 구성

### 3-1. 구성 요소의 역할

이번 실습은 다음 스택을 한 호스트에 구성한 것이다.

| 구성 요소 | 역할 |
|---|---|
| Zabbix server | 수집 데이터·트리거·이벤트를 관리하고 에이전트 데이터를 받는 중앙 서버 |
| Zabbix frontend | 브라우저에서 서버를 관리하는 PHP 웹 화면 |
| Apache 또는 Nginx | 프론트엔드에 HTTP 요청을 전달하는 웹 서버 |
| PHP | Zabbix 프론트엔드 실행 환경 |
| MariaDB/MySQL | Zabbix 설정·이력·트렌드 데이터를 저장 |
| Zabbix agent 2 | 모니터링 대상 호스트의 지표를 수집 |

따라서 이를 “APM”이라는 공식 구성요소명으로 외우기보다 **Zabbix server + DB + 웹 서버/PHP + agent**라는 웹·데이터베이스 스택으로 이해한다. PHP-FPM 사용 여부는 웹 서버 연동 방식과 배포판 패키지 구성에 따라 확인한다.

### 3-2. 공식 저장소 설치 흐름

공식 설치 페이지에서 **Zabbix 7.0 / Ubuntu 24.04 / MySQL 또는 MariaDB / Apache** 조합을 선택해 저장소 deb 파일을 받는다. 파일명 뒤 revision은 저장소에서 바뀔 수 있으므로 필기에 적힌 특정 숫자를 영구적인 값으로 외우지 않는다.

필기에서 **dkpg**라고 적은 부분은 **dpkg**가 맞다.

~~~bash
# 공식 다운로드 페이지에서 받은 Ubuntu 24.04용 Zabbix 7.0 release .deb
sudo dpkg -i ./zabbix-release_7.0-<revision>+ubuntu24.04_all.deb
sudo apt update

sudo apt install -y \
  zabbix-server-mysql \
  zabbix-frontend-php \
  zabbix-apache-conf \
  zabbix-sql-scripts \
  zabbix-agent2 \
  mariadb-server \
  apache2 \
  php-mysql
~~~

실제 패키지명과 PHP 확장 패키지는 선택한 Zabbix 7.0 패키지 저장소의 설치 안내와 설치 화면의 Required 항목을 기준으로 확인한다. 패키지 설치 후에는 서비스가 자동 시작되었는지 따로 확인한다.

### 3-3. 데이터베이스 생성

필기에 적힌 단순 비밀번호는 예시로만 남기고, 실제 시스템에서는 충분히 긴 비밀번호를 사용한다. 명령행에 비밀번호를 직접 쓰면 셸 history나 프로세스 목록에 노출될 수 있으므로 **-p 뒤를 비워 대화형으로 입력**한다.

~~~sql
CREATE DATABASE my_zabbix_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_bin;

CREATE USER 'zabbix_user'@'localhost'
  IDENTIFIED BY '강하고-긴-비밀번호';

GRANT ALL PRIVILEGES ON my_zabbix_db.* TO 'zabbix_user'@'localhost';
FLUSH PRIVILEGES;
~~~

Zabbix 사용자에게 **WITH GRANT OPTION**을 추가할 필요가 없다. 그 옵션은 해당 사용자가 다른 계정에 권한을 다시 부여할 수 있게 하므로 이 실습의 목적과 최소 권한 원칙에 맞지 않는다.

### 3-4. 스키마 가져오기

Zabbix 패키지의 SQL 스크립트를 생성한 DB에 넣는다. 정확한 테이블 수는 Zabbix 버전과 스키마에 따라 달라질 수 있으므로 “항상 203개”처럼 외우지 않는다.

~~~bash
zcat /usr/share/zabbix-sql-scripts/mysql/server.sql.gz \
  | mysql --default-character-set=utf8mb4 \
      -u zabbix_user -p my_zabbix_db
~~~

비밀번호 프롬프트에 입력한 뒤, 오류가 없는지 확인한다.

~~~bash
mysql -u zabbix_user -p my_zabbix_db -e 'SHOW TABLES;'
~~~

### 3-5. Zabbix server 설정

**/etc/zabbix/zabbix_server.conf**에 DB 연결 정보를 설정한다. 아래는 형식 예시이며, 비밀번호는 실제 값으로 바꾸되 공개 저장소에 기록하지 않는다.

~~~ini
DBName=my_zabbix_db
DBUser=zabbix_user
DBPassword=강하고-긴-비밀번호
# DBHost와 DBPort는 구성에 따라 설정한다.
# MySQL 기본 포트는 3306이다.
~~~

필기의 로그 파일 표현 **zabbix server.log**는 경로·공백이 잘못된 표기다. 실제 로그 위치는 패키지 설정과 systemd journal을 함께 확인한다.

~~~bash
sudo systemctl enable --now mariadb
sudo systemctl enable --now zabbix-server
sudo systemctl status zabbix-server --no-pager
sudo journalctl -u zabbix-server -n 100 --no-pager
~~~

### 3-6. agent 2 설정: passive와 active

**/etc/zabbix/zabbix_agent2.conf**의 주요 항목은 통신 방식에 따라 해석한다.

| 항목 | 의미 |
|---|---|
| **Server** | passive check 요청을 보낼 수 있도록 허용할 Zabbix server/proxy의 IP 또는 DNS 목록. 비워 두면 passive check가 비활성화된다 |
| **ServerActive** | agent가 먼저 접속해 active check 설정을 받을 server/proxy 주소. 비워 두면 active check가 비활성화된다 |
| **Hostname** | active check에서 서버에 등록된 호스트와 매칭하는 이름. 웹 화면의 Server name과 같은 필수 값은 아니다 |
| **ListenPort** | passive check를 받을 포트. 기본값은 10050/tcp |

예시:

~~~ini
Server=127.0.0.1
ServerActive=127.0.0.1:10051
Hostname=JHJ-Ubuntu-2404
~~~

서버 화면에서 호스트를 등록할 때 active check를 사용할 경우 **Hostname을 문자 하나까지 동일하게** 입력한다. 서버 자신을 passive 방식으로 감시하면 Server에 127.0.0.1 또는 실제 서버 주소를 사용하고, 별도 클라이언트라면 Zabbix server의 주소를 넣는다.

~~~bash
sudo systemctl enable --now zabbix-agent2
sudo systemctl status zabbix-agent2 --no-pager
sudo journalctl -u zabbix-agent2 -n 100 --no-pager
~~~

필기에서 **zabbix-agent는 Unit not found**였고 **zabbix-agent2는 active (running)**이었다. 이는 agent 1 서비스가 설치되지 않고 agent 2만 설치된 상태라면 정상적인 결과다. 두 서비스를 모두 설치해야 한다는 의미가 아니다.

### 3-7. 포트와 방화벽

| 흐름 | 기본 포트 | 필요한 경우 |
|---|---:|---|
| 브라우저 → Zabbix frontend | 80 또는 443/tcp | 웹 화면 접속 |
| Zabbix server 수신 | 10051/tcp | agent active check, trapper 등 |
| Zabbix server → agent | 10050/tcp | agent passive check |
| Zabbix server ↔ DB | 3306/tcp 또는 local socket | DB가 별도 호스트일 때. 같은 호스트면 외부 공개 불필요 |

passive만 쓸 때는 클라이언트의 10050/tcp inbound가 필요하고, active만 쓸 때는 agent가 서버의 10051/tcp로 outbound 연결할 수 있으면 된다. 10050·10051·3306을 인터넷 전체에 공개하지 않는다.

Ubuntu에서 UFW와 firewalld를 동시에 정책 관리 도구로 사용하면 규칙을 혼동할 수 있으므로 한 가지 방식을 선택한다. 수업에서 firewalld를 사용했다면 먼저 zone과 active interface를 확인한다.

~~~bash
sudo systemctl enable --now firewalld
sudo firewall-cmd --get-active-zones
sudo firewall-cmd --list-all

sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-port=10051/tcp
# passive agent를 외부에서 받을 때만, 신뢰하는 Zabbix server 주소로 제한할 것
sudo firewall-cmd --permanent --add-port=10050/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-all
~~~

실제 환경에서는 단순 포트 전체 허용보다 source 주소를 제한한 rich rule 또는 네트워크 방화벽 정책을 사용한다.

### 3-8. PHP와 웹 설치 화면

PHP 설정값은 설치 화면의 Required 값을 기준으로 조정한다. 필기에서 사용한 값 중 현재 구성에서 필요할 수 있는 예시는 다음과 같다.

~~~ini
max_execution_time = 300
memory_limit = 128M
post_max_size = 16M
upload_max_filesize = 2M
max_input_time = 300
max_input_vars = 10000
date.timezone = Asia/Seoul
~~~

**always_populate_raw_post_data**는 현대 PHP에서 더 이상 사용할 수 없는 오래된 설정이므로 새 구성에 넣지 않는다. PHP-FPM pool 파일에 값을 넣었다면 실제 PHP가 그 설정을 읽는지 확인하고 FPM 서비스를 재시작한다. 서비스명은 PHP 버전에 따라 달라진다.

~~~bash
php -v
systemctl list-units 'php*-fpm.service'
sudo systemctl restart apache2
sudo systemctl restart php8.3-fpm
~~~

마지막 명령의 **php8.3-fpm**은 실제 설치 버전에 맞춰 바꾼다.

웹 설치 화면에서 입력하는 값은 다음처럼 구분한다.

| 화면 항목 | 입력 의미 |
|---|---|
| Database type/host/name/user/password | 앞에서 만든 DB 연결 정보 |
| Server name | 웹 화면에 표시할 Zabbix server의 이름 |
| Time zone | Asia/Seoul 등 사용할 시간대 |
| Hostname | 별도의 Host 등록 화면에서 agent 설정과 맞추는 값 |

초기 계정 Admin/zabbix는 설치 직후 즉시 변경하고, 관리 화면을 인터넷에 노출하지 않는다. 설치 후 **Zabbix server is running: Yes**와 server/agent journal을 확인한다.

## 4. 실습 검증 순서

### Docker

~~~bash
docker image ls
docker ps
docker ps -a
docker inspect <container-name-or-id>
docker logs <container-name-or-id>
docker exec -it <running-container> bash
~~~

### Zabbix

~~~bash
sudo systemctl status mariadb zabbix-server zabbix-agent2 apache2 --no-pager
sudo ss -lntp | grep -E ':(80|443|10050|10051|3306)\b'
sudo journalctl -u zabbix-server -u zabbix-agent2 -n 100 --no-pager
~~~

확인할 때는 다음 순서를 지킨다.

1. DB가 실행 중이고 Zabbix schema가 대상 DB에 들어갔는지 확인한다.
2. zabbix_server.conf의 DBName, DBUser, DBPassword를 확인한다.
3. agent2가 실행 중이고 Server/ServerActive/Hostname을 확인한다.
4. ss와 방화벽으로 실제 listen 포트와 허용 방향을 확인한다.
5. 웹 화면의 서버 상태와 호스트의 agent interface/템플릿/아이템을 확인한다.

## 5. 이번 필기와 대조한 핵심 누락·중복

- Docker와 Kubernetes의 역할 경계를 분리했다.
- 이미지 태그와 latest의 의미를 수정했다.
- 컨테이너 레이어와 volume의 데이터 보존 차이를 보완했다.
- Ubuntu에 EPEL을 적용하던 설명을 배포판별 저장소 설명으로 수정했다.
- Zabbix의 DB 권한에서 WITH GRANT OPTION을 제거했다.
- dpkg 오타와 schema table count 고정 표현을 정정했다.
- Zabbix server의 10051, passive agent의 10050, active agent의 outbound 흐름을 분리했다.
- Server name과 agent Hostname의 의미를 분리했다.
- agent 서비스가 agent2만 설치된 상황을 설명했다.
- 오래된 PHP 설정과 비밀번호 노출 위험을 표시했다.

## 공식 자료

- [Docker run CLI reference](https://docs.docker.com/reference/cli/docker/container/run/)
- [Docker container runtime concepts](https://docs.docker.com/engine/containers/run/)
- [Docker storage overview](https://docs.docker.com/engine/storage/)
- [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
- [Docker glossary](https://docs.docker.com/reference/glossary/)
- [Kubernetes container runtimes](https://kubernetes.io/docs/setup/production-environment/container-runtimes/)
- [Kubernetes and Docker FAQ](https://kubernetes.io/blog/2022/02/17/dockershim-faq/)
- [Ubuntu release list](https://ubuntu.com/project/docs/release-team/list-of-releases/)
- [Zabbix 7.0 installation from packages](https://www.zabbix.com/documentation/7.0/en/manual/installation/install_from_packages)
- [Zabbix 7.0 requirements](https://www.zabbix.com/documentation/7.0/en/manual/installation/requirements)
- [Zabbix agent 2 parameters](https://www.zabbix.com/documentation/7.0/en/manual/appendix/config/zabbix_agent2)
- [Zabbix server parameters](https://www.zabbix.com/documentation/7.0/en/manual/appendix/config/zabbix_server)
