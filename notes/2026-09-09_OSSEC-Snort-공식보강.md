# 2026-09-09 OSSEC·Snort 2.9.20 실습 공식 보강

> 대상 자료: 260909-정환주.txt, ossec.txt, snort-IPS.txt, OSSEC agent-manager 실행 화면과 Windows agent 설치 화면  
> 대조 기준: 2026-09-09에 확인한 OSSEC 공식 문서, Snort 공식 문서·다운로드 페이지, Ubuntu 패키지 정보  
> 작성 원칙: 원문 필기는 보존하고, 이 문서에서 [정정], [주의], [확인 필요]를 분리한다. 모든 명령은 승인된 격리 Lab에서만 실행한다.

## 0. 먼저 기억할 결론

오늘 실습에서 가장 중요한 것은 제품의 버전과 패킷 경로를 섞지 않는 것이다.

1. Ubuntu에서 apt로 설치한 snort.conf, ipvar, config daq, config daq_mode, -Q, -i enp0s3:enp0s8 조합은 **Snort 2.9.20 계열의 inline 실습**이다. Snort 3의 snort.lua와 같은 절차가 아니다.
2. OSSEC agent를 client.keys로 등록하는 통신은 manager의 **secure 연결, 기본 UDP 1514**를 사용한다. syslog 연결은 방화벽·라우터 같은 외부 장비가 보내는 Syslog 수신용이며, agent key 교환 절차와 짝이 아니다.
3. AFPacket inline은 iptables를 자동으로 사용하는 방식이 아니다. Snort가 두 인터페이스를 직접 받아 한쪽에서 다른 쪽으로 전달하면서 검사한다. iptables/NFQUEUE는 별도의 DAQ 경로다.
4. VirtualBox의 Promiscuous Mode 허용, Linux 인터페이스의 promisc 플래그, Snort inline의 실제 패킷 경로는 서로 다른 조건이다. promisc를 켰다고 모든 트래픽이 Snort를 통과하는 것은 아니다.
5. ICMP drop 테스트가 성공하면 보통 echo reply가 돌아오지 않아 timeout이 된다. “Destination Port Unreachable”은 Snort가 ICMP echo를 차단했다는 증거가 아니며, UDP 포트에 대한 ICMP 오류와도 구분해야 한다.
6. 화면에 보이는 IP 192.168.16.76, 192.168.16.34, 필기에 적힌 192.168.16.94와 192.168.16.88/97은 **그 화면·그 시점의 Lab 값**이다. 현재 manager, agent, 테스트 클라이언트 주소를 ip -br addr와 라우팅 표로 다시 확인한 뒤 사용한다.

## 1. 필기 대조표

| 필기 또는 실행 | 판정 | 보강·정정 |
|---|---|---|
| apt install snort 후 snort.conf, ipvar, DAQ, -Q 사용 | 대체로 맞음 | Ubuntu 24.04 패키지 경로는 Snort 2.9.20으로 확인된다. 먼저 snort -V로 실제 버전을 기록한다. |
| ipvar HOME_NET 192.168.16.0/24 | 조건부 | HOME_NET은 “호스트 PC의 네트워크”가 아니라 Snort가 보호할 실제 Lab 네트워크다. 토폴로지와 주소를 확인해 정한다. |
| EXTERNAL_NET !$HOME_NET | 맞음 | Snort 2 변수 문법에서 HOME_NET의 부정 집합을 뜻한다. 이름보다 실제 관찰 방향이 중요하다. |
| “nfpacket을 통해 수집하고 iptables를 쓴다” | 부정확 | AFPacket DAQ는 Linux AF_PACKET 계열의 패킷 입출력이다. NFQUEUE DAQ를 선택할 때만 iptables/nftables가 NFQUEUE로 패킷을 넘기는 구조를 검토한다. |
| config daq: afpacket / config daq_mode: inline | 조건부로 맞음 | policy_mode:inline, -Q, 두 인터페이스의 실제 통과 경로, drop 규칙이 모두 맞아야 차단이 된다. |
| snort -T -c ... -i enp0s3:enp0s8 | 개선 필요 | -T는 설정 검증이 목적이므로 인터페이스 없이 먼저 실행한다. 인터페이스 쌍은 실제 inline 실행 때 지정한다. |
| drop icmp 192.168.16.88 ... | 조건부 | 해당 주소가 실제 테스트 클라이언트의 source IP일 때만 일치한다. 주소가 바뀌면 규칙도 매치되지 않는다. |
| OSSEC remote connection=syslog + agent key import | 정정 필요 | agent는 secure/UDP 1514와 client.keys를 사용한다. syslog는 key import 없는 외부 Syslog 송신자용이다. |
| ossec.conf의 server-ip 192.168.16.94 | 확인 필요 | 실제 manager 주소를 확인해 넣는다. 다른 주소를 넣으면 agent가 등록되어 있어도 manager에 접속하지 못한다. |
| manage_agents 메뉴에서 D가 remove | 버전 차이 | 현재 공식 4.2 문서와 화면은 A/E/L/R/Q 형식이다. 화면에 R이 보이면 R을 remove로 사용한다. |
| Windows agent 3.8.0 | 갱신 필요 | 공식 Windows 설치 문서와 화면의 4.2.0 installer를 기준으로 정리한다. 실제 설치 파일명과 manager 버전을 함께 기록한다. |
| UFW allow ssh를 OSSEC 설치 검증에 포함 | 범위 분리 필요 | SSH 접속을 위한 설정이다. OSSEC agent 통신에는 UDP 1514와 실제 활성화한 추가 서비스의 포트를 별도로 검토한다. |
| ping 결과 Destination Port Unreachable | 해석 주의 | ICMP echo를 drop한 결과로 일반적으로 기대하는 것은 응답 부재/timeout이다. 결과 문자열만으로 Snort 차단을 확정하지 말고 ingress·egress 캡처와 Snort alert를 함께 확인한다. |
| zliblg-dev, ibpcre2-dev | 오타 | zlib1g-dev, libpcre2-dev이다. 단, Atomicorp 패키지를 설치하는 경로라면 소스 빌드 의존 패키지를 전부 먼저 설치할 필요는 없다. |
| wget -q -O -https://updates.atomicorp.com/install/atomic | 오타·URL 확인 | 공백이 빠졌고, 사용한 공식 설치 경로는 https://updates.atomicorp.com/installers/atomic 이다. 실행 전 URL과 스크립트를 검토한다. |

## 2. OSSEC 구조를 정확히 이해하기

OSSEC는 호스트 기반 침입 탐지 시스템(HIDS)이다. 파일 무결성, 로그 분석, Windows registry 감시, rootkit 탐지, 실시간 경보, active response 같은 기능을 제공한다. manager가 정책·규칙·경보를 관리하고, agent가 각 운영체제에서 로그와 이벤트를 수집해 manager로 보낸다. Windows는 OSSEC에서 일반적으로 agent 역할로 사용한다.

배포판도 구분한다.

- **OSSEC upstream**: 공식 문서에 설명된 open-source OSSEC 프로젝트.
- **Atomicorp 패키지/Atomic OSSEC**: OSSEC 프로젝트를 관리·개발하는 Atomicorp가 제공하는 패키지·상용 확장·지원 경로. 필기의 updates.atomicorp.com 설치 스크립트는 이 배포 경로를 사용한다.

따라서 “OSSEC 공식 문서”의 agent 등록 절차와 “Atomicorp 패키지 설치”를 함께 쓸 수는 있지만, 보고서에는 다음을 따로 적는 것이 정확하다.

- 설치 공급원: Atomicorp repository/package
- 동작 버전: manager와 agent에서 ossec-control 또는 설치 화면으로 확인한 버전
- 설정 기준: OSSEC 4.2 공식 문서

### 2.1 agent 통신과 Syslog 통신의 차이

| 목적 | manager remote connection | 기본 포트 | 인증·특징 |
|---|---|---:|---|
| OSSEC agent | secure | UDP 1514 | client.keys로 등록하고 암호화된 agent protocol 사용 |
| 방화벽·라우터·외부 Syslog | syslog | UDP 514 | agent key 교환이 없고 allowed-ips 등으로 송신자 제한 |

manager에 다음 두 블록을 동시에 둘 수는 있지만, 각각의 목적을 섞지 않는다.

~~~xml
<!-- OSSEC agent용: client.keys와 짝을 이루는 기본 경로 -->
<remote>
  <connection>secure</connection>
  <port>1514</port>
  <protocol>udp</protocol>
</remote>

<!-- 별도 Syslog 송신자를 받을 때만 추가 -->
<remote>
  <connection>syslog</connection>
  <port>514</port>
  <protocol>udp</protocol>
  <allowed-ips>192.168.16.0/24</allowed-ips>
</remote>
~~~

agent만 연결할 때는 secure 블록을 사용하고, syslog 블록은 필요하지 않으면 만들지 않는다. 필기처럼 syslog를 설정한 뒤 client.keys를 import하면 “키 등록은 했는데 agent가 active가 되지 않는” 혼동이 생길 수 있다.

## 3. OSSEC manager 설치·초기 검증

### 3.1 설치 경로

Atomicorp 패키지 경로를 사용할 때의 Lab 예시는 다음과 같다. 실제 운영 환경에서는 외부 shell script를 바로 pipe하기 전에 URL, 서명, 변경되는 repository 설정을 검토하고 snapshot 또는 백업을 만든다.

~~~bash
sudo apt update
sudo apt install -y wget

# Lab용 Atomicorp repository 설치 경로
sudo wget -qO- https://updates.atomicorp.com/installers/atomic | sudo bash

sudo apt update
sudo apt install -y ossec-hids-server
~~~

공식 OSSEC 소스 빌드를 직접 할 때 필요한 Ubuntu 의존성은 설치 경로가 다르다. 최신 문서에는 build-essential, make, zlib1g-dev, libpcre2-dev, libevent-dev, libssl-dev, libcurl4-openssl-dev, libsystemd-dev 등이 제시된다. 필기의 zliblg-dev와 ibpcre2-dev는 패키지명이 아니다. package install과 source build의 의존성 목록을 하나의 명령으로 무조건 섞지 않는다.

설치 뒤 다음 정보를 기록한다.

~~~bash
sudo ls -ld /var/ossec
sudo /var/ossec/bin/ossec-control status
sudo /var/ossec/bin/ossec-control info
sudo grep -nE 'email_notification|<remote>|<connection>|<port>|<protocol>' \
  /var/ossec/etc/ossec.conf
~~~

### 3.2 manager 주소를 먼저 확정

agent 설정에 IP를 복사하기 전에 manager에서 다음을 실행한다.

~~~bash
ip -br addr
ip route
hostname -I
~~~

192.168.16.94는 필기에 적힌 예시일 뿐이다. 화면에 보인 192.168.16.76이 manager인지, 192.168.16.34가 Windows agent인지, 다른 인터페이스가 실제 통신망인지 토폴로지와 현재 출력으로 확인한다.

### 3.3 email_notification

~~~xml
<global>
  <email_notification>no</email_notification>
</global>
~~~

SMTP server, email_to, email_from, email_maxperhour 등이 실제로 구성되어 있을 때만 메일 알림을 활성화한다. SMTP를 준비하지 않은 Lab에서 yes로 바꾸는 것이 탐지 기능을 켜는 것은 아니다. 먼저 로컬 alerts.log와 ossec.log를 확인한다.

## 4. OSSEC agent 등록 절차

### 4.1 manager에서 key 만들기

manager에서:

~~~bash
sudo /var/ossec/bin/manage_agents
~~~

현재 공식 4.2 문서와 화면의 흐름은 다음과 같다.

1. A: agent 추가
2. agent name 입력
3. agent IP 입력. 고정 IP, CIDR 범위, 또는 필요한 경우 any를 선택하되 Lab 범위를 가능한 좁게 잡는다.
4. ID를 확인하고 y로 저장
5. L: 등록 목록 확인
6. E: key 추출
7. 화면의 key 전체를 복사한다. 앞뒤 공백·줄바꿈을 넣지 않는다.

ID 000은 manager/server 예약 ID다. 화면에 보인 001 ubuntu, 002 windows11은 해당 manager DB의 등록값이며 다른 환경에서 재사용하는 값이 아니다. key는 비밀번호와 같은 비밀값이므로 GitHub, Notion, 화면 캡처에 올리지 않는다. 이미 노출했다면 해당 agent를 재등록하거나 key를 교체한다.

agent를 추가하거나 변경한 뒤에는 manager를 재시작하고 상태를 확인한다.

~~~bash
sudo /var/ossec/bin/ossec-control restart
sudo /var/ossec/bin/ossec-control status
sudo /var/ossec/bin/agent_control -l
~~~

필기의 화면에서 메뉴가 R이면 R이 remove다. 이전 버전 자료의 D(remove)를 현재 화면에 그대로 입력하지 않는다.

### 4.2 Linux agent 설정

agent에는 manager 주소를 넣는다.

~~~xml
<client>
  <server-ip>MANAGER_IP</server-ip>
  <port>1514</port>
</client>
~~~

MANAGER_IP는 manager에서 확인한 실제 IP로 바꾼다. manager와 agent가 여러 NIC를 가졌다면 어느 인터페이스가 1514/udp를 통해 연결되는지 먼저 정한다.

agent에서:

~~~bash
sudo apt update
sudo apt install -y ossec-hids-agent
sudo vi /var/ossec/etc/ossec.conf

sudo /var/ossec/bin/manage_agents
~~~

agent의 manage_agents에서 I(import)를 선택하고 manager에서 복사한 key를 공백·줄바꿈 없이 붙여넣는다. 등록 정보가 출력되면 y로 확인한 뒤 agent를 시작한다.

~~~bash
sudo /var/ossec/bin/ossec-control start
sudo /var/ossec/bin/ossec-control status
sudo tail -f /var/ossec/logs/ossec.log
~~~

UFW가 실제로 활성화되어 있다면 manager에서 agent 통신을 허용한다.

~~~bash
sudo ufw status verbose
sudo ufw allow 1514/udp
~~~

1515/tcp는 authd를 사용한 별도 자동 등록을 구성한 경우에만 필요할 수 있다. 수동으로 manage_agents에서 key를 추출·import하는 현재 실습은 1515가 항상 열려 있어야 하는 절차가 아니다. 먼저 ss로 실제 listener를 확인한다.

~~~bash
sudo ss -lunp | grep ':1514'
sudo ss -lntup | grep ':1515'
~~~

### 4.3 Windows agent 설정

공식 Windows agent 설치 문서와 화면에 보인 4.2.0 installer를 기준으로 한다.

1. manager에서 Windows agent를 먼저 A로 등록한다.
2. manager에서 E로 해당 ID의 key를 추출한다.
3. Windows installer를 관리자 권한으로 설치한다.
4. 기본 설치 경로의 ossec.conf에서 server IP를 manager의 실제 주소로 설정한다. 화면의 경로는 C:\Program Files (x86)\ossec-agent\ossec.conf였다.
5. agent 관리 화면에 key를 붙여넣고 Manage 또는 Restart로 서비스를 재시작한다.
6. manager의 agent_control -l과 Windows agent log에서 연결 상태를 확인한다.

Windows agent가 설치됐다는 사실만으로 연결이 완료된 것은 아니다. manager ID, key, server IP, UDP 1514 경로, 서비스 실행 상태를 모두 확인해야 한다.

## 5. OSSEC 로그·규칙·진단

manager에서 먼저 볼 로그:

~~~bash
sudo tail -f /var/ossec/logs/ossec.log
sudo tail -f /var/ossec/logs/alerts/alerts.log
sudo /var/ossec/bin/agent_control -l
sudo /var/ossec/bin/agent_control -lc
sudo /var/ossec/bin/agent_control -i 001
~~~

알림이 발생하지 않을 때는 “agent가 연결되지 않음”과 “연결은 됐지만 rule이 매치되지 않음”을 분리한다.

- agent 상태가 disconnected: server-ip, manager의 secure remote, key, UDP 1514, 방화벽, 서비스 상태를 본다.
- agent가 active인데 alert가 없음: 감시할 log_location, syscheck, rootcheck, rule level, local_rules.xml, 이벤트 발생 조건을 본다.
- rule을 수정했다면 ossec-logtest로 로그 한 줄이 어떤 decoder/rule에 매치되는지 검증한다.

local_rules.xml과 client.keys는 비밀·환경 의존 자료이므로 원격 저장소에 실제 key를 넣지 않는다. 설정 변경 뒤에는 manager/agent를 재시작하고, 변경 전 파일을 별도 백업한다.

## 6. Snort 2.9.20과 Snort 3를 분리하기

| 구분 | 오늘 apt 기반 실습 | Snort 3 |
|---|---|---|
| 설정 중심 | /etc/snort/snort.conf | snort.lua |
| 변수·설정 | ipvar, config daq, config daq_mode | Lua 변수와 Snort 3 설정 구조 |
| inline 실행 | -Q, DAQ AFPacket, 인터페이스 쌍 | Snort 3의 별도 실행·설정 절차 |
| 룰·옵션 | Snort 2 문법과 옵션 | Snort 3 룰·옵션 문서 |
| 확인 방법 | snort -V, snort -T -c ... | 설치한 Snort 3 binary와 snort.lua 확인 |

Ubuntu Noble의 snort package는 2.9.20 계열이며, Snort 공식 다운로드 페이지도 Snort 2.9.20과 DAQ를 별도 릴리스 계열로 제공한다. 따라서 오늘의 snort.conf 실습은 Snort 3 설치법으로 설명하면 안 된다. Snort 3의 최신 릴리스·snort.lua·Snort 3 rule은 저장소의 2026-09-08 공식 보강 노트에서 별도로 다룬다.

먼저 실제 설치를 기록한다.

~~~bash
snort -V
dpkg-query -W snort
sudo snort --daq-list
~~~

## 7. Snort 2 Lab 네트워크와 promiscuous mode

### 7.1 주소와 인터페이스

~~~bash
ip -br link
ip -br addr
ip route
sudo ip link set dev enp0s3 up
sudo ip link set dev enp0s8 up
sudo ip link set dev enp0s3 promisc on
sudo ip link set dev enp0s8 promisc on
ip link show enp0s3
ip link show enp0s8
~~~

Linux에서 promisc를 켜는 것은 인터페이스가 수신할 프레임의 조건을 바꾸는 것이다. 재부팅·링크 재생성 뒤 유지된다고 가정하지 않는다. VirtualBox 설정의 어댑터 Promiscuous Mode “Allow All”도 하이퍼바이저가 guest에 프레임을 전달할 조건을 바꾸는 별도 설정이다.

두 설정 모두 켜도 Snort를 거치지 않고 같은 L2/L3 경로로 통신하면 inline drop은 보이지 않는다. AFPacket inline에서는 enp0s3:enp0s8처럼 연결한 두 포트 사이에 실제 Lab 트래픽이 흘러야 한다. Snort 공식 AFPacket IPS 문서의 방식은 Snort가 이 두 인터페이스를 직접 처리하므로 Linux bridge를 미리 만드는 절차가 필수는 아니다.

### 7.2 HOME_NET

예를 들어 보호할 Lab 세그먼트가 정말 192.168.16.0/24라면:

~~~conf
ipvar HOME_NET 192.168.16.0/24
ipvar EXTERNAL_NET !$HOME_NET
~~~

그러나 이 값은 화면에 보이는 host IP의 네트워크 주소를 기계적으로 복사하는 항목이 아니다. 여러 인터페이스, NAT, Host-only/Internal Network, 라우터를 사용하면 보호 대상과 관리망이 달라질 수 있다. 실제 의도에 맞지 않으면 rule이 맞아도 경보 방향이 달라진다.

## 8. Snort 2 inline 설정과 local rule

### 8.1 설정 항목

snort.conf에 다음 역할이 모두 있는지 확인한다. 줄 번호는 배포판의 conf 파일에 따라 달라지므로 필기처럼 758번 같은 위치를 고정하지 않는다.

~~~conf
config policy_mode: inline
config daq: afpacket
config daq_mode: inline
config logdir: /var/log/snort
~~~

또한 local.rules가 실제로 include되어야 한다.

~~~conf
include $RULE_PATH/local.rules
~~~

확인:

~~~bash
grep -nE 'policy_mode|config daq|daq_mode|logdir|local.rules' /etc/snort/snort.conf
sudo snort --daq-list
~~~

### 8.2 rule 매치 범위

실제 테스트 클라이언트 주소를 SOURCE_IP에 넣어 사용한다. SOURCE_IP가 바뀌면 이전 rule은 매치되지 않는다.

~~~conf
drop icmp SOURCE_IP any -> $HOME_NET any (msg:"ICMP Drop Test"; sid:1000001; rev:1;)
~~~

예를 들어 실제 source가 192.168.16.88인 Lab에서만:

~~~conf
drop icmp 192.168.16.88 any -> $HOME_NET any (msg:"ICMP Drop Test"; sid:1000001; rev:1;)
~~~

이 rule은 source IP가 192.168.16.88인 ICMP가 HOME_NET으로 향할 때 매치한다. 192.168.16.97에서 보냈다면 rule이 동작하지 않는다. 여러 승인된 Lab 클라이언트를 시험할 때는 하나의 주소에 매달리지 말고 필요한 범위만 명시한다.

### 8.3 설정 검증과 실행

먼저 설정만 검증한다.

~~~bash
sudo snort -T -c /etc/snort/snort.conf
~~~

-T가 성공해도 traffic path가 맞다는 뜻은 아니다. conf syntax, rule load, DAQ 모듈을 검증하는 단계다.

그 다음에만 AFPacket inline을 실행한다.

~~~bash
sudo snort -A console -Q -c /etc/snort/snort.conf -i enp0s3:enp0s8
~~~

Snort 공식 AFPacket IPS 절차의 핵심 조건은 다음 네 가지다.

1. policy mode를 inline으로 설정
2. AFPacket DAQ와 inline mode 사용
3. 실행 시 -Q 지정
4. drop 또는 reject처럼 inline response가 필요한 rule 사용

passive IDS로 실행하거나 인터페이스 하나만 감시하면 drop rule이 실제 경로에서 차단하지 않을 수 있다. AFPacket 경로에는 iptables 규칙을 추가하지 않는다. NFQUEUE DAQ를 별도로 선택했을 때만 firewall이 NFQUEUE로 패킷을 넘기는 구조를 설계한다.

## 9. ICMP drop 테스트의 올바른 판정

테스트는 자신이 만든 격리 Lab의 client와 target 사이에서만 수행한다.

1. 테스트 client에서 ping -c 3 TARGET_IP를 실행한다.
2. Snort console에 ICMP Drop Test alert가 나타나는지 본다.
3. enp0s3 ingress와 enp0s8 egress를 각각 tcpdump로 관찰해 packet이 어느 쪽까지 갔는지 확인한다.
4. rule source IP, HOME_NET, 인터페이스 순서, 실제 route를 다시 확인한다.

~~~bash
sudo tcpdump -ni enp0s3 icmp
sudo tcpdump -ni enp0s8 icmp
~~~

drop이 실제로 매치되면 echo request가 반대쪽으로 전달되지 않아 일반적으로 echo reply가 오지 않고 timeout이 된다. 운영체제나 라우터가 별도 ICMP 오류를 만들 수 있으므로, “Destination Port Unreachable” 한 줄을 Snort drop의 증거로 사용하지 않는다. 특히 port unreachable은 ICMP type 3/code 3인 UDP 관련 오류와 연관된 표현이다.

실습을 끝내면 Ctrl+C로 Snort를 종료하고, 임시로 켠 promisc가 필요하지 않다면 원복한다.

~~~bash
sudo ip link set dev enp0s3 promisc off
sudo ip link set dev enp0s8 promisc off
~~~

## 10. 문제 해결 순서

| 증상 | 먼저 볼 것 | 흔한 원인 |
|---|---|---|
| snort -T 실패 | error가 가리키는 줄, local.rules include, rule 문법 | Snort 2/3 문법 혼용, 오타, 누락된 include |
| DAQ afpacket 없음 | snort --daq-list, 설치된 snort/daq package | DAQ package 누락 또는 다른 binary 실행 |
| alert는 뜨지만 통신이 통과 | 실행 명령의 -Q, policy_mode, daq_mode, 실제 interface pair | passive 모드, 다른 경로 우회, drop rule 미로드 |
| alert가 안 뜸 | source IP, HOME_NET, rule include, console/log | 192.168.16.88/97 불일치, 목적지 방향 불일치 |
| 모든 통신이 끊김 | enp0s3:enp0s8 순서와 VM 연결, 관리 SSH 경로 | inline pair가 실제 관리망을 끊음 |
| OSSEC agent disconnected | server-ip, manager secure/1514, client.keys, service, UDP path | syslog 설정을 agent 설정으로 사용, key 공백, 잘못된 manager IP |
| agent는 active인데 alert 없음 | ossec.log, alerts.log, ossec-logtest, 감시 설정 | 연결과 탐지 규칙을 한 문제로 판단 |
| Windows agent 설치 완료 후 미연결 | 관리자 권한 설치, service restart, server IP, key | manager 등록·key 추출을 생략하거나 오래된 버전 절차 사용 |

## 11. 제출용 최종 체크리스트

- [ ] manager/agent/Windows의 실제 IP와 역할을 표로 기록했다.
- [ ] OSSEC manager와 agent 버전을 각각 확인했다.
- [ ] OSSEC manager의 agent 연결은 secure/UDP 1514로 설정했다.
- [ ] syslog가 필요하지 않으면 syslog remote block을 만들지 않았다.
- [ ] manager에서 A → E, agent에서 I 순서로 key를 등록했다.
- [ ] key와 client.keys를 GitHub·Notion·스크린샷에 노출하지 않았다.
- [ ] manager restart, agent start, ossec-control status, agent_control -l을 확인했다.
- [ ] Snort 실제 버전이 2.9.20 계열인지 snort -V로 기록했다.
- [ ] snort.conf와 snort.lua를 섞지 않았다.
- [ ] local.rules include, policy_mode:inline, DAQ afpacket/inline을 확인했다.
- [ ] -T 설정 검증과 -Q inline 실행을 분리했다.
- [ ] drop rule의 source IP와 HOME_NET이 실제 Lab 토폴로지와 일치한다.
- [ ] traffic이 두 인터페이스 쌍을 실제로 통과하는지 캡처로 확인했다.
- [ ] ping 결과 문구만이 아니라 alert와 ingress/egress 관찰로 차단을 판정했다.
- [ ] 실습 종료 후 임시 promisc와 서비스 상태를 원복·기록했다.

## 출처

### OSSEC 공식

- [OSSEC 공식 홈페이지 — HIDS와 Atomicorp의 프로젝트 관리·지원 설명](https://www.ossec.net/)
- [OSSEC 4.2 문서](https://www.ossec.net/docs/)
- [OSSEC 설치 요구사항](https://www.ossec.net/docs/docs/manual/installation/installation-requirements.html)
- [OSSEC 소스 설치와 manager UDP 1514](https://www.ossec.net/docs/docs/manual/installation/install-source.html)
- [OSSEC agent 관리: add/extract/import/restart](https://www.ossec.net/docs/docs/manual/agent/agent-management.html)
- [OSSEC remote 설정: secure와 syslog](https://www.ossec.net/docs/docs/syntax/head_ossec_config.remote.html)
- [OSSEC client 설정: server-ip와 event port](https://www.ossec.net/docs/docs/syntax/head_ossec_config.client.html)
- [OSSEC Windows agent 설치](https://www.ossec.net/docs/docs/manual/installation/installation-windows.html)
- [ossec-control](https://www.ossec.net/docs/docs/programs/ossec-control.html)
- [agent_control](https://www.ossec.net/docs/docs/programs/agent_control.html)
- [OSSEC 로그 FAQ](https://www.ossec.net/docs/docs/faq/ossec.html)
- [ossec-logtest](https://www.ossec.net/docs/docs/programs/ossec-logtest.html)
- [Atomicorp 패키지 업데이트 안내](https://www.ossec.net/docs/docs/manual/installation/updates.html)

### Snort 공식·Ubuntu 패키지

- [Ubuntu Noble snort package — 2.9.20 계열](https://packages.ubuntu.com/noble/snort)
- [Snort 공식 다운로드](https://www.snort.org/downloads)
- [Snort DAQ README](https://www.snort.org/document/readme-daq)
- [Snort IPS using DAQ AFPacket](https://www.snort.org/documents/snort-ips-using-daq-afpacket)
- [Snort active response/drop](https://www.snort.org/document/readme-active)
- [Snort 2 variables: ipvar와 부정 변수](https://www.snort.org/document/readme-variables)
- [Snort 3 공식 시작 문서](https://docs.snort.org/start/)
- [Snort 3 공식 rule 문서](https://docs.snort.org/rules/)
- [Snort 공식 EOL 공지](https://blog.snort.org/2026/01/end-of-life-announcement-for-versions.html)

관련 Snort 3·Suricata·DDoS·Wireshark·ASA·pfSense 내용은 저장소의 [2026-09-08 공식 보강 노트](2026-09-08_DDoS-Snort-Suricata-ASA-Failover-pfSense-Wireshark-공식보강.md)와 분리해 읽는다.
