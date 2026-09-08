# 2026-09-08 수업 메모 공식 보강

> 대상: snort_install.txt, 이론(1).txt, 260908-메모(1).txt, 26.09.03(1).zip 및 기존 보안·네트워크 학습 노트  
> 확인일: **2026-09-08 (UTC)**  
> 원칙: 기존 수업 메모는 보존하고, 공식 문서와 맞지 않거나 실습 조건에 따라 달라지는 부분을 [정정], [주의], [확인 필요]로 보완한다.

## 0. 먼저 읽어야 할 결론

- DDoS의 정확한 풀이는 **Distributed Denial of Service**이다. “Distribute Denial of Service”는 잘못된 표현이다.
- **hping3 --flood**, 무작위 출발지 주소, 대량 전송은 실제 서비스에 장애를 일으킬 수 있다. 아래 명령은 승인된 소유 실습망에서 아주 작은 횟수로 패킷을 관찰할 때만 사용한다.
- Linux의 promiscuous mode는 NIC가 수신한 프레임을 더 넓게 커널에 전달하도록 하는 설정일 뿐, 스위치 전체 트래픽을 자동으로 복제하지 않는다. SPAN/TAP/inline 경로 또는 올바른 VM 토폴로지가 별도로 필요하다.
- Snort의 **-c**는 설정 파일 지정, **-T**는 설정 테스트, **-i**는 라이브 인터페이스, **-Q**는 지원되는 DAQ를 이용한 inline 모드다. **-i**만 붙인 Snort는 일반적으로 수동 탐지 모드이며 IPS가 아니다.
- Suricata YAML에 **inline: yes**를 적는 것만으로 IPS가 되지 않는다. Linux에서는 NFQUEUE 또는 AF_PACKET inline처럼 실제 패킷 경로와 큐/인터페이스를 연결해야 한다.
- ASA의 **http server enable**은 일반 웹 서버를 여는 명령이 아니라 ASDM의 HTTPS 관리 서비스와 허용 출발지 목록을 설정하는 명령이다.
- Wireshark의 캡처 필터와 표시 필터는 문법과 동작 시점이 다르다. 캡처 필터는 BPF/pcap 문법, 표시 필터는 Wireshark display-filter 문법을 사용한다.

## 1. 첨부 메모에서 확인된 범위

| 자료 | 확인된 주제 | 보강 방향 |
|---|---|---|
| snort_install.txt | Snort NIC promiscuous/offload systemd 서비스 | 서비스가 Snort 엔진을 실행하지 않는 점, 인터페이스·부팅 타이밍·검증 방법 보완 |
| 이론(1).txt | DDoS, hping3, tcpdump/Wireshark, Snort 3, Suricata | 용어·필터·패킷 크기·IPS 조건·최신 버전 정정 |
| 260908-메모(1).txt | IDS/IPS, Snort 3 룰, Apache 테스트, Rocky Suricata | 경로 오타, 옵션 의미, 룰 의미, 규칙 소스·로그·검증 절차 보완 |
| 26.09.03(1).zip | ASA failover, pfSense OpenVPN, ASA/IOS 관리, Wireshark, Cisco debug | 장비별 명령 의미 분리, 인증서·stateful failover·필터 문법·안전 주의 보완 |

화면 캡처에만 근거한 IP·메뉴·버전은 특정 실습 환경의 값이므로 운영 환경의 기본값으로 쓰면 안 된다.

## 2. DoS/DDoS와 hping3

### 2.1 용어와 공격면

| 용어 | 정확한 의미 | 메모에서 보완할 점 |
|---|---|---|
| DoS | 하나의 출발점 또는 한정된 출발점이 서비스 가용성을 떨어뜨리는 공격/장애 유발 | 공격자의 수보다 정상 요청을 처리하지 못하는 결과가 핵심 |
| DDoS | 여러 호스트·봇넷·분산 출발점에서 동시에 발생하는 DoS | Distributed가 정확한 표기이며 “PC 여러 대로 ping”과 동의어는 아님 |
| Volumetric | 링크·대역폭·처리량을 소진시키는 공격 | UDP/ICMP flood 등이 예가 될 수 있음 |
| Protocol/state exhaustion | SYN backlog, connection tracking, 방화벽 상태 같은 자원을 소진 | “sym fludding”은 **SYN flooding**으로 정정 |
| Application-layer | 웹 worker, connection, CPU, 메모리 등 애플리케이션 자원을 소진 | Slow HTTP, 큰 요청을 오래 유지하는 유형 |
| ICMP flood | 많은 ICMP Echo Request 등으로 처리량·CPU·링크를 압박 | Ping of Death와 분리해야 함 |
| Ping of Death | 과거 비정상적으로 큰/조각화된 ICMP 처리 취약점을 노린 역사적 공격명 | 단순한 ICMP 대량 전송이 아님 |

Large Chunk, Slow HTTP, SYN flood, ICMP flood는 서로 다른 계층의 자원 고갈 예다. 하나의 실습 트래픽으로 모든 DDoS 유형이 재현되는 것은 아니다.

### 2.2 실습 안전 경계

1. 대상은 본인이 소유하거나 명시적인 승인을 받은 VM·사설망으로 제한한다.
2. 인터넷으로 라우팅되지 않는 호스트 전용/내부 네트워크를 사용하고 브리지 모드는 피한다.
3. 정상 응답시간·CPU·메모리·연결 수를 먼저 측정하고 작은 횟수·낮은 속도부터 시작한다.
4. **--flood**, 무작위 출발지 주소, 출발지 위조는 일반 실습 절차에 포함하지 않는다. 강사 통제 아래 격리된 재현망에서만 별도 승인한다.
5. 종료 후 hping3·캡처·Snort/Suricata 프로세스와 임시 firewall rule·promiscuous/offload 설정을 확인하고 원복한다.

### 2.3 hping3 옵션

| 옵션 | 의미 | 오해하기 쉬운 점 |
|---|---|---|
| **-S** | TCP SYN 플래그 설정 | SYN 패킷을 만드는 옵션이지 DDoS 판정 옵션이 아님 |
| **-c 20** | 지정한 횟수만 전송 | 실제 전송량은 옵션·인터페이스·응답에 따라 달라짐 |
| **-d 1000** | TCP/UDP payload 크기 지정 | MTU·분할·세그먼트·드롭에 따라 결과가 달라짐 |
| **-a 주소** | 출발지 주소 위조 | 응답을 받을 수 없고 anti-spoofing에서 차단될 수 있음 |
| **--rand-source** | 무작위 출발지 주소 사용 | 반사·오용 위험이 큼 |
| **--flood** | 가능한 빠르게 전송 | 속도·영향을 예측하기 어렵고 서비스 장애를 만들 수 있음 |

개념 확인용 최소 예시는 대상과 횟수를 명시한다. **<LAB_TARGET_IP>**는 격리된 실습 VM의 실제 주소로만 치환한다.

~~~bash
# 승인된 격리 실습망에서만: 제한된 SYN 패킷을 관찰
sudo hping3 <LAB_TARGET_IP> -S -c 20
~~~

**-d 10000**은 “10000바이트짜리 하나의 완성된 Ethernet 패킷”을 만든다는 뜻이 아니다. IP 총 길이·TCP 세그먼트·NIC offload·MTU·캡처 지점에 따라 달라진다. “1000 byte로 6개가 한 패킷” 같은 고정 숫자는 삭제하고 실제 캡처의 **frame.len**, **ip.len**, **tcp.len**, fragmentation/segmentation 필드를 확인한다.

### 2.4 관찰·대응

**top**, **htop**, **btop**은 호스트 자원 변화를 보는 도구이고, **tcpdump**/Wireshark는 패킷을 보는 도구다. 둘을 합쳐 링크·CPU·연결 추적 테이블 중 어디가 병목인지 추론한다.

DDoS 대응은 공격자 역추적 하나로 끝나지 않는다. CISA 관점의 탐지·기록, rate limiting/filtering, upstream ISP 또는 DDoS 보호 서비스 연계, 장애 시 우회·복구, anti-spoofing과 사후 분석을 함께 준비한다. 실습에서 ping을 방화벽에서 막는 것은 특정 ICMP 정책의 예일 뿐 모든 DDoS의 해결책은 아니다.

## 3. IDS/IPS와 promiscuous mode

| 구분 | 위치/동작 | 핵심 |
|---|---|---|
| NIDS | 네트워크 구간 관찰 | 미러 포트/TAP/inline 경로와 센서 위치가 범위를 결정 |
| HIDS | 호스트 파일·프로세스·로그·이벤트 관찰 | 네트워크 패킷 센서와 역할이 다름 |
| IDS | 탐지·경보·기록 | 보통 패킷을 통과시키거나 차단하지 않는 수동 관찰 |
| IPS | 트래픽 경로에서 허용/차단/drop/reject | inline 경로·성능·fail-open/close 설계가 필요 |

### 3.1 Linux와 VirtualBox 설정 분리

~~~bash
ip link show dev enp0s3
sudo ip link set dev enp0s3 promisc on
ip link show dev enp0s3       # PROMISC 확인
sudo ip link set dev enp0s3 promisc off  # 종료 시 원복
~~~

**PROMISC**는 NIC가 자신에게 지정된 MAC 이외의 수신 프레임도 커널로 전달하도록 하는 설정이다. 일반 스위치는 센서 MAC으로 향하지 않은 유니캐스트를 센서 포트에 보내지 않으므로 다음 중 하나가 별도로 필요하다.

- 스위치 SPAN/mirror 포트
- 네트워크 TAP 또는 허브
- 센서가 트래픽 경로 안에 있는 inline 구성
- 센서 guest가 실제로 트래픽을 볼 수 있는 내부/호스트 전용 VM 토폴로지

VirtualBox의 **Promiscuous Mode: Allow All**은 hypervisor의 guest NIC 전달 정책이다. guest OS의 **ip link ... promisc on**과 별개이며, 브리지 네트워크의 가시성 정책을 보조할 뿐 스위치 미러링을 대신하지 않는다.

### 3.2 GRO/LRO와 캡처

~~~bash
sudo ethtool -k enp0s3 | grep -E 'gro|lro|gso|tso'
sudo ethtool -K enp0s3 gro off lro off
~~~

GRO/LRO/GSO/TSO는 성능을 위한 offload 기능이다. 캡처 지점과 드라이버에 따라 보이는 패킷 크기·분할 단위에 영향을 줄 수 있어 재현 실습에서 일시적으로 끌 수 있다. CPU 사용량이 늘 수 있고 재부팅·NetworkManager 정책으로 원복될 수 있으므로 “Snort 설치 필수”가 아니라 “관찰 결과 단순화를 위한 선택”으로 기록한다.

첨부된 **snort3-nic.service**는 promiscuous mode와 GRO/LRO만 변경하는 **oneshot** 서비스다. **RemainAfterExit=yes**는 명령 성공 후 active 상태로 남기는 의미이며, Snort 탐지 프로세스를 시작하지 않는다. **WantedBy=default.target**은 수업 환경에서 동작할 수 있지만 서버 서비스에는 **multi-user.target**과 인터페이스 의존성·검증을 검토한다.

## 4. Snort 3 설치·실행 공식 대조

### 4.1 현재 버전과 재현성

확인일 기준 공식 Snort 3 최신 릴리스는 **3.12.2.0**, 릴리스가 표시한 의존성은 **LibDAQ v3.0.27**, **LibML v2.0.0**이다. 버전은 바뀔 수 있으므로 **master.zip**은 재현성이 낮다. 보고서에는 Snort·LibDAQ·LibML·OS·compiler 버전을 함께 기록한다.

공식 다운로드 페이지의 versioned source archive와 Talos rule 정보를 사용하고, 반복 실습에는 해당 날짜의 release/tag 또는 archive checksum을 고정한다.

### 4.2 빌드 원칙

수업의 빌드 흐름은 개념적으로 맞다.

~~~bash
git clone https://github.com/snort3/libdaq.git
cd libdaq
./bootstrap
./configure
make -j"$(nproc)"
sudo make install
sudo ldconfig
~~~

재현용이라면 LibDAQ **v3.0.27**, Snort **3.12.2.0** 같은 공식 release tag/archive를 기록한다. clone/configure/make는 일반 사용자로 수행할 수 있고, **/usr/local** 설치와 **ldconfig**처럼 시스템 경로를 바꾸는 단계만 관리자 권한이 필요하다.

**--enable-tcmalloc**과 gperftools는 선택적 성능 최적화다. 기본 빌드를 먼저 성공시킨 뒤 성능 비교에서 별도로 사용한다.

### 4.3 핵심 실행 옵션

| 명령/옵션 | 의미 |
|---|---|
| **snort -V** | 버전·빌드 정보 확인 |
| **-c /path/snort.lua** | 설정 파일 지정 |
| **-T** | 설정·구성 요소 validation |
| **-i enp0s3** | 라이브 인터페이스에서 수집 |
| **-R /path/local.rules** | 룰 파일 추가 로드 예 |
| **-A alert_fast** | fast alert logger 선택 |
| **-s 65535** | 캡처 snap length |
| **-k none** | checksum 검사 비활성화; VM 실습에서만 임시 사용 |
| **-Q** | 지원 DAQ·구성에서 inline 실행 |

~~~bash
sudo snort -c /usr/local/etc/snort/snort.lua -T
sudo snort -V
~~~

**-c**만으로 구성 로딩을 확인하는 예도 있지만 자동화·보고서에서는 **-T**를 명시한다. **-Q**와 실제 inline DAQ/경로가 준비되지 않았다면 Snort를 IPS라고 부르지 않는다.

### 4.4 설정 변수와 룰 경로

~~~lua
HOME_NET = '[실제로 보호할 실습망 CIDR]'
EXTERNAL_NET = '!$HOME_NET'
~~~

**HOME_NET**은 실제 보호 대상 네트워크다. **EXTERNAL_NET = '!$HOME_NET'**은 HOME_NET이 아닌 네트워크라는 표현이지 항상 공용 인터넷을 뜻하지 않는다.

경로 오타를 정정한다.

~~~bash
sudo mkdir -p /usr/local/etc/snort/rules
sudo touch /usr/local/etc/snort/rules/local.rules
~~~

메모의 **/local/etc/snort/**는 **/usr/local/etc/snort/**로 고쳐야 한다. **local.rules**는 파일이므로 **mkdir**가 아니라 **touch**를 사용한다. include 위치는 설치 방법·버전에 따라 다르므로 줄 번호보다 **snort.lua**의 ips/rule path 설정을 확인한다.

### 4.5 룰과 ICMP 테스트

~~~text
alert icmp any any -> $HOME_NET any (msg:"ICMP Echo Request observed"; sid:1000001; rev:1;)
~~~

일반적인 룰 구조는 **action protocol source direction destination (options)**이며 모든 조건이 맞을 때 action이 실행된다. 위 룰은 ICMP 관찰 예이지 DDoS 확정 룰이 아니다. 단일 ping과 DDoS를 구분하려면 threshold/rate, 출발지·목적지·시간창, 서버 지표를 함께 설계한다.

SID는 기존 룰과 충돌하지 않게 관리한다. **msg**에는 관찰 사실을 쓰고 공격 판정은 별도 상관분석에서 수행한다.

~~~bash
sudo snort \
  -c /usr/local/etc/snort/snort.lua \
  -R /usr/local/etc/snort/rules/local.rules \
  -i enp0s3 \
  -A alert_fast \
  -s 65535
~~~

**-k none**은 VM checksum offload 때문에 테스트가 이상할 때만 임시로 붙인다. **systemctl status apache2**는 웹 서버 상태 확인일 뿐 Snort가 트래픽을 보았다는 증거가 아니므로 alert·pcap·서버 access log를 상호 대조한다.

## 5. Suricata: Rocky/RHEL 계열과 IPS 조건

### 5.1 패키지·경로

수업의 명령은 실습 이미지에서의 시작점이다.

~~~bash
sudo dnf install -y epel-release
sudo dnf install -y suricata
sudo suricata-update
sudo systemctl enable --now suricata
~~~

Rocky/RHEL 버전과 저장소 정책에 따라 EPEL, CRB, OISF COPR와 Suricata major version이 달라질 수 있다. 설치 직후 다음을 기록한다.

~~~bash
suricata --build-info
suricata -V
sudo suricata -T -c /etc/suricata/suricata.yaml -v
~~~

RPM의 흔한 위치는 다음과 같지만 **suricata.yaml**의 **default-rule-path**, **rule-files**, **log-dir**가 최종 기준이다.

| 목적 | 흔한 RPM 경로 |
|---|---|
| 설정 | **/etc/suricata/**, **/etc/sysconfig/suricata** |
| 룰 | **/var/lib/suricata/rules/**, **/etc/suricata/rules/** |
| 로그 | **/var/log/suricata/** |
| EVE JSON | **/var/log/suricata/eve.json** |

**fast.log**, **eve.json**, **stats.log**, **suricata.log** 생성만으로 룰이 맞았다는 뜻은 아니다. EVE의 event type/signature, fast.log의 SID/message, 입력 인터페이스와 캡처를 함께 확인한다.

### 5.2 룰 소스와 local.rules

**suricata-update**는 규칙을 내려받고 활성화·비활성화·업데이트하는 공식 관리 도구다.

~~~bash
sudo suricata-update update-sources
sudo suricata-update list-sources
# list-sources 결과에서 실제 source 이름을 확인
sudo suricata-update enable-source <SOURCE_NAME>
sudo suricata-update
~~~

메모의 **enable-source et/open**은 도구가 현재 표시하는 source 이름과 일치할 때만 사용한다. ET Open은 무료 규칙 세트의 예이며 모든 상용·Talos 규칙이 무료라는 뜻은 아니다.

직접 만든 룰은 배포판 설정의 **rule-files**에 포함하거나 일회성 테스트에서 **-s**로 명시한다.

~~~bash
sudo suricata -T -c /etc/suricata/suricata.yaml \
  -s /etc/suricata/rules/local.rules -v
~~~

**-s**가 기본 rule loading과 결합되는 방식은 **suricata --help**와 설정을 확인한다. YAML 줄 번호에 의존하지 않는다.

### 5.3 IDS에서 IPS로 바뀌는 조건

Suricata 공식 IPS는 실제 트래픽 필터링이다.

- NFQUEUE: 방화벽이 패킷을 NFQUEUE로 보내고 Suricata가 **-q <queue>**로 verdict를 반환한다. **suricata --build-info**에서 NFQ 지원을 확인한다.
- AF_PACKET inline: 두 인터페이스 사이 L2 경로와 copy-mode/copy-iface를 구성한다.
- 환경에 따라 DPDK, IPFW 등의 경로도 사용될 수 있다.

따라서 **inline: yes** 단일 키만으로 IPS가 되지 않는다. 실제 데이터 경로·DAQ/커널 지원·**drop/reject** 룰·방화벽 queue 또는 inline 인터페이스·장애 시 동작을 함께 검증한다. 처음에는 **alert**, 승인된 격리망에서만 **drop**을 검증한다.

## 6. ASA Active/Standby Failover

### 6.1 첨부 토폴로지

첨부 그림의 **1.1.1.0/24**는 실제 공인 주소로 사용하면 안 된다. 그림을 재현할 때도 격리된 GNS3/에뮬레이터 안에서만 사용하고, 새 실습에는 RFC 5737 문서용 대역 또는 사설 대역을 선택한다.

| 항목 | Primary | Secondary | 용도 |
|---|---:|---:|---|
| inside | **192.168.250.1/24** | **192.168.250.2/24** | 내부 인터페이스 주소/standby |
| outside | **1.1.1.1/24** | **1.1.1.2/24** | 그림의 lab-only 외부 구간 |
| failover link | **172.16.0.1/24** | **172.16.0.2/24** | failover 제어·설정 동기화 |

**failover lan interface**는 logical name과 물리 인터페이스를 연결하고, **failover interface ip**는 primary/standby IP를 지정한다. **failover link**는 failover/state link를 지정하며 마지막 **failover**가 기능을 활성화한다. 양쪽 인터페이스·이름·마스크·키·primary/secondary 역할이 맞아야 한다.

### 6.2 Configuration state와 Stateful state

- Configuration/state synchronization: running configuration, role, 일부 상태를 동기화한다.
- Stateful failover: 별도 또는 공유 state link로 연결 상태, NAT/ARP 등 지속해야 하는 connection state를 전달한다.

**show failover**에 stateful이라는 단어가 보이는 것만으로 state link 설계가 끝난 것은 아니다. 트래픽이 많은 환경은 전용 state link를 권장하고 사용자 data 경로와 failover 링크를 분리한다. ASA 모델·소프트웨어별 지원 차이는 실제 configuration guide를 기준으로 한다.

~~~text
show failover
show failover history
show monitor-interface
show running-config failover
~~~

active/standby 역할, failover/state link, monitored interface, peer 도달성, configuration mismatch, history를 확인한다. **gi0/2**를 failover link로 쓰는 동안 사용자 data interface로 동시에 사용하지 않는다.

## 7. pfSense와 Remote-access OpenVPN

### 7.1 용어와 화면 범위

pfSense는 FreeBSD 기반 오픈소스 firewall/router 플랫폼이다. **UTM**은 여러 보안 기능을 묶은 제품 범주이므로 pfSense와 동의어가 아니다. 첨부 화면의 pfSense **2.7.2-RELEASE**, WAN DHCP, LAN **10.10.18.254/24**는 당시 실습 환경의 값이다.

설치 직후 WAN/LAN, 관리 GUI의 프로토콜·허용 인터페이스, DHCP, 관리자 비밀번호를 기록한다. 화면에 보인 비밀번호·키·인증서 private key는 문서·Git에 남기지 않고 즉시 변경·마스킹한다.

### 7.2 OpenVPN remote-access 의존 관계

1. local users 또는 LDAP/RADIUS 같은 authentication source를 결정한다.
2. Certificate Manager에서 CA를 만들거나 신뢰할 CA를 준비한다.
3. CA가 서명한 server certificate와 필요 시 사용자별 client certificate를 발급한다.
4. **VPN > OpenVPN > Wizards**에서 Remote Access Server를 만들고 authentication source, certificate, Tunnel Network, local network를 지정한다.
5. OpenVPN server와 WAN/interface firewall rule을 최소 권한으로 확인한다.
6. Client Export package를 설치한 뒤 **VPN > OpenVPN > Client Export**에서 profile을 내보낸다.
7. OpenVPN GUI/client로 연결하고 pfSense OpenVPN status·firewall log·client route·내부 서비스 접근을 상호 검증한다.

CA는 인증서를 서명하는 신뢰 앵커이고 server certificate와 client certificate/key는 다른 역할이다. “발급기관을 먼저 만들고 인증서를 생성”한다는 메모는 이 의존 관계를 말한다. client private key와 TLS key는 공유·커밋하지 않는다.

**Allow communication** 같은 체크박스나 메뉴 위치는 버전·패키지에 따라 달라질 수 있다. 체크 표시보다 생성된 firewall rule, Tunnel Network, local route, 인증서 chain, 연결 로그를 결과로 기록한다. 연결됐지만 내부망 접근이 안 되면 OpenVPN status만 보지 말고 interface rule·routing·firewall을 확인한다.

### 7.3 점검표

- [ ] WAN/LAN IP와 gateway가 의도한 격리망에 있다.
- [ ] WebConfigurator는 필요한 인터페이스·HTTPS에만 열려 있다.
- [ ] 관리자 초기 비밀번호를 변경했고 문서에 secret을 남기지 않았다.
- [ ] CA → server certificate → client certificate chain이 유효하다.
- [ ] Tunnel Network가 LAN·기존 VPN 대역과 겹치지 않는다.
- [ ] OpenVPN server와 firewall rule이 필요한 포트·출발지만 허용한다.
- [ ] Client Export profile과 키를 안전하게 전달하고 분실 시 인증서를 폐기한다.
- [ ] 연결 후 내부 DNS/웹 서비스, route, firewall log를 확인한다.

## 8. ASA 관리 HTTP와 IOS Telnet/SSH

### 8.1 ASA ASDM 관리

다음은 ASA의 ASDM 관리 허용 설정으로 해석한다.

~~~text
http server enable
http <관리자_출발지_IP> <마스크> inside
~~~

**http server enable**은 ASDM 관리용 HTTPS 서비스를 제공하고, **http source mask interface**는 관리 접속 허용 출발지를 제한한다. 일반 Apache HTTP 서버를 켜는 명령이 아니다. **192.168.100.200 255.255.255.255**는 단일 호스트 허용 예이며 운영에서는 관리망/점프 호스트만 허용한다.

### 8.2 ASA Telnet과 IOS Router VTY 분리

ASA Telnet 허용은 IOS router의 VTY 설정과 다르다. Telnet은 평문이므로 운영 관리에는 SSH를 사용하고, Telnet은 폐쇄 실습에서만 재현한다.

IOS에서 **login local**은 local username database를 사용하므로 **enable password**만으로 VTY 로그인 설정이 되지 않는다.

~~~text
username <사용자> privilege 15 secret <실습용-임시-비밀번호>
line vty 0 4
 login local
 transport input ssh
~~~

구형 실습에서만 **transport input telnet**을 제한된 망에 사용하고 완료 후 SSH only로 되돌린다. secret을 소스·스크린샷·Git에 기록하지 않는다.

## 9. Wireshark와 tcpdump 필터

### 9.1 캡처 필터와 표시 필터

| 구분 | 적용 시점 | 예 |
|---|---|---|
| Capture filter | 캡처 전에 수집량을 줄임; BPF/pcap | **icmp**, **host 192.168.16.27**, **tcp port 80**, **tcp and host 192.168.16.27** |
| Display filter | 이미 캡처한 패킷을 화면에서 선택 | **icmp**, **ip.addr == 192.168.16.27**, **tcp.port == 80**, **http.request** |

Wireshark 표시 필터의 논리 연산은 **&&/and**, **||/or**, **!/not**을 사용한다.

~~~text
icmp && ip.addr == 192.168.16.27
tcp.flags.syn == 1 && tcp.flags.ack == 0
tcp.port == 80 || tcp.port == 443
~~~

캡처 필터의 예:

~~~text
icmp and host 192.168.16.27
tcp port 80 or tcp port 443
~~~

메모의 **&**와 **::**는 일반적인 AND/OR 표기가 아니다. display filter에서 **&**는 비트 연산 등 다른 의미가 될 수 있고 **::**는 논리 OR가 아니다. 필터 입력 칸의 초록색/빨간색은 문법 유효성 피드백이지 공격 판정이 아니다.

### 9.2 분석 순서와 화면 표시

권장 순서는 **필터링 → 관심 패킷 표시/마크 → 분석 → 통계·대화·Endpoint 확인 → 필요하면 Follow TCP Stream → 증거와 한계 기록 → 정책 수정·재검증**이다.

색상화 규칙은 가독성을 위한 시각화 설정이다. packet mark는 분석자의 표시일 뿐 패킷 내용을 변경하지 않는다. **Follow TCP Stream**은 TCP stream의 양방향 payload를 재구성해 보는 기능이며 화면 색은 방향을 구분하는 UI 표현이다. TLS/암호화 트래픽은 payload가 평문으로 보이지 않을 수 있다.

**tcpdump**는 libpcap 기반 CLI 캡처·간단 분석 도구이고 Wireshark는 GUI 분석기다. 같은 pcap도 캡처 지점·NIC offload·필터 시점에 따라 결과가 달라질 수 있다.

## 10. Cisco debug와 원격 관찰

~~~text
show debugging
debug ip ospf hello
undebug all
~~~

**debug ip packet**은 트래픽이 많은 장비에서 CPU·콘솔을 급격히 사용할 수 있다. 가능하면 ACL로 제한한 **debug ip packet <ACL> [detail]**을 사용하고 VTY에서는 **terminal monitor**를 켠다. 지원 여부는 **debug ip ospf ?**, **debug ?**로 먼저 확인한다. **u all**은 **undebug all**의 축약이므로 문서에는 명시형을 적는다.

SPAN/TAP에서 패킷을 보는 것과 IOS 내부 debug 출력을 보는 것은 별개다. 전자는 Wireshark/tcpdump 증거, 후자는 장비 프로세스가 해석한 이벤트이므로 timestamp와 interface를 맞춰 상호 검증한다.

## 11. 메모 오류·중복·누락 정리

| 원문 표현/절차 | 판정 | 보강·정정 |
|---|---|---|
| Distribute Denial of Service | 오탈자 | Distributed Denial of Service |
| sym fludding | 오탈자 | SYN flooding |
| Ping of Death = ICMP flood | 개념 혼동 | 역사적 malformed/oversized ICMP와 일반 ICMP flood를 분리 |
| --flood, --rand-source를 기본 실습 명령으로 제시 | 과도한 위험 | 승인된 격리망·제한 속도·작은 count만 기본값 |
| -d 10000이면 고정 개수 패킷 | 부정확 | payload 크기일 뿐; MTU/분할/offload에 따라 결과가 달라짐 |
| promiscuous mode면 네트워크 전체 수신 | 과장 | SPAN/TAP/inline/VM 토폴로지 필요 |
| snot | 오탈자 | Snort |
| /local/etc/snort/... | 경로 오타 | /usr/local/etc/snort/... |
| local.rules에 mkdir | 파일·디렉터리 혼동 | rules는 mkdir -p, 파일은 touch |
| -c만으로 IPS가 됨 | 옵션 혼동 | -c config, -T test, -i live passive, -Q 지원 DAQ 기반 inline |
| Snort NIC service를 Snort service로 설명 | 역할 혼동 | NIC tuning oneshot과 탐지 엔진 service를 분리 |
| Suricata inline: yes만 설정 | 불충분 | NFQUEUE/AF_PACKET 등 실제 inline 경로·drop rule·firewall 연결 |
| Suricata rule source를 무조건 유료라고 설명 | 과도한 일반화 | ET Open 등 무료 source와 상용 source를 구분 |
| http server enable = HTTP 웹 서버 | 장비 의미 오류 | ASA ASDM HTTPS 관리 서비스 |
| ASA 명령과 IOS line vty 명령을 하나로 설명 | 플랫폼 혼동 | ASA 관리와 IOS VTY/SSH 설정을 분리 |
| enable password + login local만으로 VTY 설정 | 누락 | local username database와 transport input ssh를 함께 구성 |
| &, :: = Wireshark AND/OR | 필터 문법 오류 | capture/display 언어에 맞춰 and/&&, or/|| 사용 |
| debug 실행 후 계속 방치 | 운영 위험 | 범위 제한 후 undebug all, show debugging |

## 12. 통합 검증 체크리스트

### DDoS/hping3

- [ ] 실습망이 인터넷으로 라우팅되지 않고 대상·승인 범위를 기록했다.
- [ ] 전후 CPU/메모리/연결 수/정상 응답 시간을 비교했다.
- [ ] count·payload·간격을 기록했고 flood/spoof를 기본값으로 사용하지 않았다.
- [ ] tcpdump capture filter와 Wireshark display filter를 구분했다.
- [ ] 패킷 수·payload·MTU/분할·서버 로그를 함께 확인했다.

### Snort/Suricata

- [ ] -V/--build-info와 설치 버전을 기록했다.
- [ ] snort -T 또는 suricata -T가 성공했다.
- [ ] HOME_NET·인터페이스·rule path가 실제 실습 대역과 일치한다.
- [ ] alert의 pcap/SID/message와 서버 로그를 상호 대조했다.
- [ ] IDS와 IPS를 구분했고 inline은 격리 테스트에서만 검증했다.

### ASA/pfSense

- [ ] ASA peer 역할·failover link·state link·monitored interface를 show 명령으로 확인했다.
- [ ] failover link를 사용자 data 경로와 분리했다.
- [ ] pfSense CA/server/client 인증서와 Tunnel Network가 겹치지 않는다.
- [ ] 비밀번호와 private key가 문서·Git에 남지 않았다.
- [ ] OpenVPN status뿐 아니라 route·firewall log·내부 서비스 접근을 검증했다.

## 13. 공식 출처

확인일은 모두 **2026-09-08**이며 제품 버전과 UI는 이후 바뀔 수 있다.

- [CISA: Understanding and Responding to Distributed Denial-of-Service Attacks](https://www.cisa.gov/resources-tools/resources/understanding-and-responding-distributed-denial-service-attacks)
- [Snort 3 공식 설치 문서](https://docs.snort.org/start/installation)
- [Snort 3 공식 도움말·실행 옵션](https://docs.snort.org/start/help)
- [Snort 3 inspection / passive와 inline](https://docs.snort.org/start/inspection)
- [Snort 3 rule 문법](https://docs.snort.org/rules/)
- [Snort 3 최신 릴리스](https://github.com/snort3/snort3/releases/tag/3.12.2.0)
- [LibDAQ 최신 릴리스](https://github.com/snort3/libdaq/releases/tag/v3.0.27)
- [Snort 공식 다운로드·Talos rule 안내](https://www.snort.org/downloads)
- [Suricata User Guide](https://docs.suricata.io/)
- [Suricata IPS 개념](https://docs.suricata.io/en/suricata-8.0.6/ips/ips-concept.html)
- [Suricata Linux NFQUEUE inline 설정](https://docs.suricata.io/en/suricata-8.0.6/ips/setting-up-ipsinline-for-linux.html)
- [Suricata rule management / suricata-update](https://docs.suricata.io/en/suricata-8.0.0/rule-management/suricata-update.html)
- [Netgate pfSense OpenVPN remote access](https://docs.netgate.com/pfsense/en/latest/recipes/openvpn-ra.html)
- [Netgate OpenVPN Client Export](https://docs.netgate.com/pfsense/en/latest/packages/openvpn-client-export.html)
- [Cisco ASA 9.20 HA failover](https://www.cisco.com/c/en/us/td/docs/security/asa/asa920/configuration/general/asa-920-general-config/ha-failover.html)
- [Cisco ASA management / ASDM HTTP 명령](https://www.cisco.com/c/en/us/td/docs/security/asa/asa919/configuration/general/asa-919-general-config/admin-management.html)
- [Wireshark display filter guide](https://www.wireshark.org/docs/wsug_html_chunked/ChWorkBuildDisplayFilterSection.html)
- [Wireshark capture filter 문법](https://www.wireshark.org/docs/man-pages/pcap-filter.html)
- [Wireshark display filter reference](https://www.wireshark.org/docs/dfref/)
- [VirtualBox networking manual](https://www.virtualbox.org/manual/ch06.html)
- [Linux ip-link manual](https://man7.org/linux/man-pages/man8/ip-link.8.html)
- [Linux kernel segmentation offloads](https://docs.kernel.org/networking/segmentation-offloads.html)
- [RFC 5737: IPv4 Address Blocks Reserved for Documentation](https://www.rfc-editor.org/rfc/rfc5737)
