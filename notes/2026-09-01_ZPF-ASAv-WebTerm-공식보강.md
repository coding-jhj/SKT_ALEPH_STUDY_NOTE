# 2026-09-01 수업 보강 · ZPF·ASAv·GNS3 WebTerm 공식 대조

> 첨부 필기에서 확인한 실습 결과를 기준으로 중복을 줄이고, Cisco·Docker·GNS3 공식 문서와 대조해 명령의 역할·기본 정책·예외·검증 순서를 보강한 문서다. `[실습 관찰]`은 첨부 출력에서 확인한 결과, `[공식 확인]`은 공식 문서와 맞춘 내용, `[이미지 의존]`은 IOS/ASA/Docker/GNS3 이미지에 따라 재검증해야 하는 내용이다.

## 0. 오늘 배운 내용을 한 문장으로

ZPF는 IOS 라우터에서 `zone → zone-pair → class-map → policy-map → service-policy`를 이어 방향별 상태 기반 정책을 만들고, ASAv는 `nameif → security-level → transit ACL/access-group 또는 관리 접속 명령`을 분리하여 판단하며, WebTerm은 주소·직접 연결망·default gateway·실제 TCP 서비스가 모두 맞아야 최종 접속이 된다.

## 1. 첨부 필기에서 실제로 확인된 사실

- R2에 `inside`, `outside` zone을 만들고 FastEthernet0/0, 0/1을 각각 가입시켰다.
- zone-pair만 만든 단계에서 `service-policy not configured`가 표시됐다.
- `permit ip any any`를 class-map에 매치하고 `inspect`를 연결하자 IOS가 “특정 프로토콜이 없어 모든 프로토콜을 검사한다”고 경고했다.
- 그 뒤 inside에서 시작한 R1→R4 ping과 Telnet이 성공했고, outside에서 시작한 R4→R1 ping과 `10.10.10.1:80` 접속은 실패했다.
- `show policy-map type inspect zone-pair sessions`에서 R1의 임시 포트에서 R4의 Telnet 23번으로 향하는 `SIS_OPEN` 세션이 보였다.
- WebTerm-1에 `192.168.100.200/24`를 넣고 다른 서브넷의 `192.168.200.254`를 gateway로 넣으려 하자 `Nexthop has invalid gateway`가 났고, 같은 서브넷의 `192.168.100.254`로 바꾸자 명령이 받아들여졌다.
- R2의 `ip http server`와 `ip http secure-server`는 IOS 라우터의 관리 서버 명령이며, ASAv의 `http server enable`과 같은 명령이 아니다.
- 필기 마지막의 `time-range timetest`와 ACE의 `time-range testtime`은 이름이 달라 수정해야 한다.

## 2. ZPF 보강

아래는 위 실습의 올바른 개념과 재현 명령이다.
## 085. ZFW — 공식 보강 본문

> Cisco 공식 문서의 명칭은 **Zone-Based Policy Firewall(ZPF 또는 ZBF)**이다. 이 교재에서는 수업에서 사용한 ZFW라는 표현을 병기한다. 아래 설정은 IOS 라우터의 ZPF 실습 기준이며, 장비 IOS 이미지에 따라 지원되는 검사 프로토콜과 출력 문구는 달라질 수 있다.

### 1. Zone-Based Policy Firewall의 핵심

ZPF는 인터페이스에 ACL 한 장을 거는 방식에서 나아가, 보안 요구가 같은 인터페이스를 논리적 `zone`으로 묶고 `zone-pair`와 `service-policy`로 구간별 트래픽을 통제한다. 중요한 것은 “zone을 만들었다”와 “통신을 허용했다”가 같은 뜻이 아니라는 점이다.

- 같은 zone에 속한 인터페이스 사이의 트래픽은 기본적으로 허용된다.
- 서로 다른 zone 사이의 트래픽은 zone-pair와 정책이 없으면 기본 차단된다.
- zone 인터페이스와 zone에 가입하지 않은 인터페이스 사이의 트래픽도 일반적으로 차단되므로, 모든 데이터 인터페이스의 소속을 먼저 정해야 한다.
- `self`는 라우터 자신이 속한 시스템 정의 zone이다. 라우터를 목적지·출발지로 하는 관리 트래픽을 통제하려면 self가 포함된 정책을 별도로 설계해야 한다.
- 하나의 인터페이스는 한 zone에만 가입할 수 있고, zone-pair는 `source → destination` 한 방향으로 정의된다.

### 2. Zone, zone-pair, 정책의 관계

트래픽이 통과하려면 다음 세 층이 이어져야 한다.

1. **Zone**: 인터페이스를 inside, outside, dmz 같은 논리 영역에 가입시킨다.
2. **Zone-pair**: 출발 zone과 목적 zone의 방향을 선언한다.
3. **Service-policy**: zone-pair에 policy-map을 연결하여 실제로 inspect, pass, drop 중 하나를 적용한다.

zone-pair만 만들고 `show zone-pair security`에서 `service-policy not configured`가 보이면, 방향만 존재할 뿐 허용·검사 정책은 아직 연결되지 않은 상태다. 다른 zone에서 반대 방향으로 새 세션을 시작하려면 별도의 reverse zone-pair가 필요하다.

### 3. ACL은 최종 허용표가 아니라 class-map의 분류 조건이다

ZPF에서 ACL을 class-map에 연결할 때 ACL의 의미는 일반적인 “여기서 permit이면 방화벽이 최종 허용한다”와 다르다.

- ACL의 `permit` ACE에 맞는 패킷은 그 class-map에 **매치**된다.
- ACL의 `deny` ACE에 맞는 패킷은 그 class-map에 **매치되지 않는다**. 다른 class나 `class-default`로 계속 평가될 수 있다.
- 최종 동작은 policy-map의 `inspect`, `pass`, `drop`이 결정한다.
- `permit ip any any`는 모든 IPv4 트래픽을 분류하는 매우 넓은 조건이다. 첨부 실습에서 나온 “특정 프로토콜이 없으므로 모든 프로토콜을 검사한다”는 경고는 이 설정의 범위를 그대로 설명한다. 학습용 확인 뒤에는 서비스·출발지·목적지를 최소 범위로 줄인다.

### 4. 실습 구성 예시

아래는 inside에서 outside로 ICMP, HTTP, Telnet을 시험하기 위한 최소 예시다. 실제 운영에서는 Telnet 대신 SSH를 사용하고, `any any` 대신 정확한 네트워크·호스트·포트를 적는다.

```cisco
R2# configure terminal
R2(config)# zone security inside
R2(config-sec-zone)# exit
R2(config)# zone security outside
R2(config-sec-zone)# exit
R2(config)# interface FastEthernet0/0
R2(config-if)# zone-member security inside
R2(config-if)# exit
R2(config)# interface FastEthernet0/1
R2(config-if)# zone-member security outside
R2(config-if)# exit

R2(config)# ip access-list extended ACL-INSIDE-OUT
R2(config-ext-nacl)# permit icmp any any
R2(config-ext-nacl)# permit tcp any any eq 23
R2(config-ext-nacl)# permit tcp any any eq 80
R2(config-ext-nacl)# exit
R2(config)# class-map type inspect match-any CM-INSIDE-OUT
R2(config-cmap)# match access-group name ACL-INSIDE-OUT
R2(config-cmap)# exit
R2(config)# policy-map type inspect PM-INSIDE-OUT
R2(config-pmap)# class type inspect CM-INSIDE-OUT
R2(config-pmap-c)# inspect
R2(config-pmap-c)# exit
R2(config-pmap)# class class-default
R2(config-pmap-c)# drop
R2(config-pmap-c)# exit
R2(config-pmap)# exit
R2(config)# zone-pair security ZP-INSIDE-OUT source inside destination outside
R2(config-sec-zone-pair)# service-policy type inspect PM-INSIDE-OUT
R2(config-sec-zone-pair)# end
```

`inspect`는 허용한 첫 방향의 세션 상태를 만들고, 그 세션에 속하는 응답 트래픽을 역방향 zone-pair 없이 되돌려 보낼 수 있게 하는 상태 기반 동작이다. 반대로 `pass`는 패킷을 통과시키지만 세션을 만들지 않으므로, 응답 방향 정책을 별도로 허용해야 한다. `drop`은 차단이며, 명시하지 않은 패킷은 class-default로 간다.

### 5. 첨부 실습 결과 해석

- zone과 인터페이스를 만든 직후 `R1 → 10.10.30.4`와 `R4 → 10.10.10.1` ping이 실패했다. 이것은 주소·경로가 반드시 틀렸다는 뜻이 아니라, 서로 다른 zone 사이에 정책이 없다는 ZPF 기본 동작과 일치한다.
- `zone-pair security inout source inside destination outside`만 만든 직후 `service-policy not configured`가 표시되었다. 이 단계는 정책 미연결 상태다.
- `permit ip any any`를 class-map에 매치하고 `inspect`를 연결한 뒤에는 `R1 → R4` ping과 Telnet이 성공했다. inside에서 시작한 세션의 응답이 검사 상태를 통해 돌아온 것이다.
- 반대로 `R4 → R1` ping과 `R4 → 10.10.10.1:80` 접속은 실패했다. outside에서 시작하는 reverse 정책이 없기 때문이다. 단, 최종 원인 확정에는 `show ip route`, 인터페이스 상태, 목적지 서비스 리스닝 상태도 함께 확인한다.
- `SIS_OPEN`으로 표시된 `10.10.10.1:49097 → 10.10.30.4:23` 세션은 R1의 임시 출발 포트에서 R4의 Telnet 포트로 만들어진 검사 세션이다. 숫자 `49097`은 서비스 포트가 아니라 클라이언트 임시 포트다.

### 6. 확인 명령어

```cisco
R2# show zone security
R2# show zone-pair security
R2# show zone-pair security ZP-INSIDE-OUT
R2# show access-lists ACL-INSIDE-OUT
R2# show class-map type inspect
R2# show policy-map type inspect
R2# show policy-map type inspect zone-pair
R2# show policy-map type inspect zone-pair sessions
R2# show ip interface brief
R2# show ip route
```

ACL 카운터가 0이면 패킷이 ACL에 도달하지 않았거나 다른 ACL/경로를 통과하고 있을 수 있다. class-map 매치 카운터, policy-map의 inspect/drop 카운터, 세션 목록을 순서대로 보면 “주소·경로 문제”와 “정책 문제”를 분리할 수 있다. IOS의 ZPF와 기존 CBAC의 `ip inspect`를 같은 인터페이스에 무심코 혼용하지 않는 것도 중요하다.

### 7. ZPF 삭제 순서

참조 중인 policy-map이나 zone을 먼저 지우면 의존성 오류가 날 수 있다. 실습을 초기화할 때는 정책 연결부터 끊는다.

```cisco
R2# configure terminal
R2(config)# zone-pair security inout
R2(config-sec-zone-pair)# no service-policy type inspect policytest
R2(config-sec-zone-pair)# exit
R2(config)# no zone-pair security inout
R2(config)# no policy-map type inspect policytest
R2(config)# no class-map type inspect classtest
R2(config)# no ip access-list extended acltest
R2(config)# interface FastEthernet0/0
R2(config-if)# no zone-member security inside
R2(config-if)# exit
R2(config)# interface FastEthernet0/1
R2(config-if)# no zone-member security outside
R2(config-if)# exit
R2(config)# no zone security inside
R2(config)# no zone security outside
R2(config)# end
```

장비가 특정 명령을 자동으로 정리하는 IOS 이미지라면 `show running-config`로 남은 참조를 확인한다. 삭제 명령은 운영 장비가 아닌 격리된 실습 장비에서만 실행한다.

### 8. 구성 흐름 요약

`인터페이스 주소·라우팅 확인 → zone 생성 → zone-member 지정 → 방향별 zone-pair 생성 → ACL로 분류 → class-map 연결 → policy-map의 inspect/pass/drop 결정 → zone-pair에 service-policy 연결 → 카운터·세션·실제 서비스로 검증` 순서로 기억하면 된다.

## 128. ASAv — 공식 보강 본문

> ASAv는 ASA 방화벽의 가상 어플라이언스다. 따라서 IOS 라우터의 `ip http server`, ZPF의 `zone security`와 ASA의 `http server enable`, `nameif`, `security-level`을 같은 명령 체계로 섞으면 안 된다.

### 1. ASAv 기본 설정

ASAv의 인터페이스는 단순히 IP 주소만 넣는 것으로 끝나지 않는다. `nameif`로 ASA 내부에서 사용할 논리 이름을 부여하고, `security-level`로 기본 보안 관계를 명시한다. 아래 주소는 첨부 실습의 예시이며 실제 GNS3 포트 번호·주소는 토폴로지에서 확인한다.

```cisco
ciscoasa# configure terminal
ciscoasa(config)# interface GigabitEthernet0/0
ciscoasa(config-if)# nameif inside
ciscoasa(config-if)# security-level 100
ciscoasa(config-if)# ip address 1.1.1.2 255.255.255.0
ciscoasa(config-if)# no shutdown
ciscoasa(config-if)# exit
ciscoasa(config)# interface GigabitEthernet0/1
ciscoasa(config-if)# nameif outside
ciscoasa(config-if)# security-level 0
ciscoasa(config-if)# ip address 2.2.2.2 255.255.255.0
ciscoasa(config-if)# no shutdown
ciscoasa(config-if)# end
```

`inside`를 이름으로 사용하고 보안 레벨을 생략하면 ASA가 100을 부여하는 버전이 있지만, 의도를 명확히 하려면 실습에서도 `security-level 100`을 직접 적는 편이 좋다. 다른 이름의 기본값은 0이다. `nameif`는 단순 별칭이 아니라 ASA의 정책·라우팅·관리 명령이 인터페이스를 참조하는 기준이다.

### 2. ASAv 동작 모드

- **Routed mode**: 각 인터페이스에 L3 주소를 두고 라우팅·NAT·ACL을 적용하는 일반적인 실습 모드다.
- **Transparent mode**: 브리지처럼 동작하며 L2 구간에 배치한다. Routed mode에서 쓰는 주소·라우팅 실습과 동작 방식이 다르다.
- ASAv 부팅과 인터페이스 인식에는 시간이 걸릴 수 있다. GNS3에서 링크가 보인다는 것과 ASA 데이터 플레인이 준비됐다는 것은 다르므로 콘솔의 부팅 완료와 `show interface ip brief`를 확인한다.

### 3. 보안 레벨의 기본 동작

ASA의 security level은 0부터 100까지다. 기본적으로 보안 레벨이 높은 인터페이스에서 낮은 인터페이스로 나가는 유니캐스트 IPv4/IPv6 트래픽은 허용되고, 낮은 곳에서 높은 곳으로 시작하는 트래픽은 허용되지 않는다. 이것은 “모든 것이 항상 통과”한다는 뜻이 아니다.

- 인터페이스 ACL, NAT, 라우팅, 서비스 리스닝 상태가 모두 별도로 만족되어야 한다.
- TCP·UDP처럼 상태를 추적할 수 있는 흐름은 허용된 연결의 반환 트래픽이 자동으로 연관된다.
- ICMP는 TCP처럼 일반적인 연결 상태로 추적되지 않으므로, ping 왕복은 ICMP inspection 또는 양방향 ACL 등 별도 조건이 필요하다. 따라서 “높은 곳에서 낮은 곳은 ICMP를 제외하고 전부 허용”이라고 외우기보다, ICMP의 상태 처리와 실제 정책을 확인한다.
- 같은 security level의 서로 다른 인터페이스 사이 통신은 기본적으로 차단되며, 필요하면 `same-security-traffic permit inter-interface`를 검토한다. 한 인터페이스로 나갔다가 같은 인터페이스로 돌아오는 hairpin은 `permit intra-interface`가 별도다.
- ASAv 자체를 목적지로 하는 SSH·ASDM·Telnet은 transit 트래픽이 아니라 관리 plane 접속이다. security level만으로 관리 접속이 열리지 않는다.

### 4. 필기 명령의 정확한 역할

다음 세 비밀번호를 구분해야 한다.

- `enable password`: privileged EXEC 모드 진입용이다.
- `passwd`: ASA가 AAA를 사용하지 않을 때 Telnet 로그인에 쓰는 비밀번호다. SSH·ASDM 사용자 계정을 만드는 명령이 아니다.
- `username ... password ...`: ASA의 로컬 사용자 데이터베이스에 계정을 만든다. SSH·HTTP/ASDM에서 `LOCAL` AAA와 함께 사용한다.

필기에 나온 `1234`는 실습용 예시일 뿐 실제 장비나 인터넷에 연결된 관리면에서 재사용하지 않는다. IOS 라우터에서 `line vty` 아래 `password`와 `login`을 쓰는 것 역시 VTY 회선 비밀번호 방식이며, 운영·보안 실습에서는 로컬 사용자와 SSH를 우선한다.

### 5. IOS 라우터 관리 서버와 ASA 관리 서버의 차이

IOS 라우터에서:

```cisco
R2(config)# hostname R2
R2(config)# ip domain-name lab.example
R2(config)# username admin privilege 15 secret [LAB_SECRET]
R2(config)# crypto key generate rsa modulus 2048
R2(config)# ip ssh version 2
R2(config)# line vty 0 4
R2(config-line)# login local
R2(config-line)# transport input ssh
R2(config-line)# exit
R2(config)# no ip http server
R2(config)# ip http secure-server
```

`ip http server`는 일반 HTTP, `ip http secure-server`는 HTTPS 서버를 켠다. 두 명령을 모두 넣으면 평문 HTTP도 남을 수 있으므로 HTTPS만 필요할 때는 `no ip http server`를 명시한다. 첨부 로그의 1024-bit RSA 생성은 실습 이미지에서 동작한 결과이지만, 새 구성에서는 이미지가 지원하는 더 큰 키를 사용한다.

### 6. OSPF 라우팅 설정: ASA와 IOS의 마스크 표기 차이

ASA의 OSPF `network` 명령은 일반 서브넷 마스크를 사용한다. IOS 라우터의 OSPF `network` 명령은 와일드카드 마스크를 사용하므로 다음 두 줄을 혼동하지 않는다.

```cisco
ciscoasa(config)# router ospf 1
ciscoasa(config-rtr)# router-id 2.2.2.2
ciscoasa(config-rtr)# network 1.1.1.0 255.255.255.0 area 0
ciscoasa(config-rtr)# network 2.2.2.0 255.255.255.0 area 0
ciscoasa(config-rtr)# log-adj-changes

R1(config)# router ospf 1
R1(config-router)# network 1.1.1.0 0.0.0.255 area 0
R1(config-router)# network 10.10.10.0 0.0.0.255 area 0
```

OSPF 인접성이 안 되면 방화벽 정책 전에 양쪽 인터페이스가 같은 서브넷인지, area·hello/dead timer·network type·router ID가 맞는지, ASA가 routed mode인지부터 확인한다.

### 7. 확인 명령어와 관리 plane/transit plane 구분

```cisco
ciscoasa# show nameif
ciscoasa# show interface ip brief
ciscoasa# show running-config interface
ciscoasa# show running-config route
ciscoasa# show running-config access-list
ciscoasa# show service-policy
ciscoasa# show ssh
ciscoasa# show crypto key mypubkey rsa
```

목적지가 ASAv 자신이면 ASA의 `ssh`, `http`, `telnet` 허용 명령을 확인한다. ASAv를 지나 내부 WebTerm이나 서버로 가는 패킷이면 인터페이스 ACL과 `access-group`을 확인한다. 이 둘을 분리해야 “ping은 되는데 ASDM이 안 된다” 또는 “ASDM은 되는데 내부 웹 서버가 안 된다”를 정확히 설명할 수 있다.

## 129. ASAv ACL·ASDM — 공식 보강 본문

> 이 절의 ACL은 ASAv를 **통과하는 transit 트래픽**을 제어한다. ASAv 자체로 들어오는 SSH·ASDM·Telnet 관리 접속은 별도의 to-the-box 관리 명령을 쓴다.

### 1. 방화벽 ACL 정책 개요

ASA 인터페이스 ACL은 첫 번째로 일치하는 ACE를 적용한다. 일치하는 줄이 없으면 암묵적 deny가 적용되므로, 허용 줄의 순서와 범위를 함께 설계해야 한다. ACL을 만들기만 해서는 동작하지 않고 `access-group`으로 인터페이스에 적용해야 한다.

### 2. ASA ACL 명령어 구조

ASA extended ACL의 기본 모양은 다음과 같다.

```text
access-list [ACL이름] extended [permit|deny] [프로토콜] [출발지] [목적지] [목적지 포트·옵션]
```

출발지와 목적지를 모두 적어야 한다. 네트워크는 일반 서브넷 마스크, 단일 호스트는 `host IP`, 전체는 `any`로 표현한다. IOS extended ACL의 와일드카드 마스크와 ASA ACL의 서브넷 마스크를 섞지 않는다.

첨부 필기의 `access-list httpoutside extended permit tcp host 192.168.200.100 eq www`는 목적지 주소가 빠져 있어 완전한 extended ACE가 아니다. `permit any any`도 프로토콜 자리가 없으므로 올바른 ASA 문법이 아니다. 모든 IPv4를 임시로 허용하려면 문법상 `permit ip any any`지만, 실습 확인 뒤 즉시 제거해야 한다.

### 3. 외부 WebTerm에서 내부 WebTerm으로 HTTP 허용 예시

아래 예시는 `192.168.200.100`이 외부 출발지, `192.168.100.200`이 내부 웹 서버인 경우다. HTTP 서비스가 실제로 80번에서 리스닝하는지도 별도로 확인한다.

```cisco
ciscoasa(config)# access-list OUTSIDE-IN extended permit tcp host 192.168.200.100 host 192.168.100.200 eq www
ciscoasa(config)# access-list OUTSIDE-IN extended permit tcp host 192.168.200.100 host 192.168.100.200 eq https
ciscoasa(config)# access-group OUTSIDE-IN in interface outside
```

`access-group OUTSIDE-IN in interface outside`는 outside 인터페이스로 들어오는 transit 패킷에 OUTSIDE-IN을 적용한다. ASA 8.3 이상에서 NAT를 사용한다면 ACL의 주소는 일반적으로 NAT 전의 real address 기준으로 작성하므로, 실제 NAT 구성도 함께 확인한다.

### 4. ICMP, 보안 레벨, ACL의 상호작용

ping 성공 여부는 HTTP·SSH 성공 여부와 동일하지 않다. ICMP echo/echo-reply를 ACL로 직접 제어한다면 양방향을 생각해야 하며, ASA 정책 맵에서 ICMP inspection을 사용하는 방식도 있다. 높은 security level에서 낮은 곳으로 나가는 ping이 보안 레벨만으로 왕복한다고 단정하지 말고 `show service-policy`, ACL 카운터, 패킷 추적을 확인한다.

또한 보안 레벨의 implicit permit보다 명시적 interface ACL이 우선하여 트래픽을 제한할 수 있다. 반대로 ACL에 `permit ip any any`를 넣으면 학습 중에는 원인 분리가 쉬워 보여도 실제 방화벽의 최소 권한 경계를 없앤다.

### 5. ASAv 자체의 SSH·ASDM·Telnet 관리 접속

다음 명령은 ASAv 자신으로 접속할 관리 호스트를 허용한다. 관리망의 실제 대역으로 좁혀 쓰며, outside에 광범위하게 열지 않는다.

```cisco
ciscoasa(config)# username whoti password [LAB_PASSWORD] privilege 15
ciscoasa(config)# aaa authentication ssh console LOCAL
ciscoasa(config)# aaa authentication http console LOCAL
ciscoasa(config)# crypto key generate rsa modulus 2048
ciscoasa(config)# ssh 192.168.100.0 255.255.255.0 inside
ciscoasa(config)# http server enable
ciscoasa(config)# http 192.168.100.0 255.255.255.0 inside
ciscoasa(config)# passwd [LAB_PASSWORD]
ciscoasa(config)# telnet 192.168.100.0 255.255.255.0 inside
```

`http server enable`은 ASA의 HTTP 관리 서버 명령 이름이지만 ASDM 접속은 기본적으로 HTTPS 443 포트를 사용한다. 브라우저에서는 `https://[ASA관리주소]`로 접속하며, 평문 HTTP가 열렸다고 해석하지 않는다. SSH는 `username`과 `aaa authentication ssh console LOCAL`이 연결되어야 로컬 계정 인증을 사용할 수 있다. Telnet은 평문이므로 격리된 실습에서만 사용하고 outside에는 허용하지 않는 것이 원칙이다.

관리 plane 명령인 `ssh`, `http`, `telnet`은 ASAv 자신에 대한 접속 허용 목록이다. 이것을 transit ACL로 대체할 수 없고, 반대로 내부 서버로 가는 transit 트래픽을 관리 명령만으로 허용할 수도 없다.

### 6. 시간·로그·비활성화 옵션

`time-range` 이름은 ACL에서 정의한 이름과 한 글자까지 같아야 한다. 필기에는 `time-range timetest`를 만들고 ACE에서는 `testtime`을 사용했으므로 서로 다른 이름이다.

```cisco
ciscoasa(config)# time-range timetest
ciscoasa(config-time-range)# periodic weekdays 09:00 to 18:00
ciscoasa(config-time-range)# exit
ciscoasa(config)# access-list OUTSIDE-IN extended permit tcp host 2.2.2.1 host 1.1.1.1 eq telnet time-range timetest
ciscoasa(config)# access-list OUTSIDE-IN extended permit tcp host 2.2.2.1 host 1.1.1.1 eq 443 log informational
ciscoasa(config)# access-list OUTSIDE-IN extended permit ip any any inactive
```

`inactive`는 ACE를 설정에 남겨 둔 채 평가에서 제외하고, `log`는 매치 이벤트를 로깅한다. 허용 범위가 넓은 ACE를 아래에 추가해 앞의 deny를 우회하지 않도록 first-match 순서를 확인한다.

### 7. 확인·장애 분석 명령어

```cisco
ciscoasa# show running-config access-list
ciscoasa# show access-list OUTSIDE-IN
ciscoasa# show access-group
ciscoasa# show service-policy
ciscoasa# packet-tracer input outside tcp 192.168.200.100 49152 192.168.100.200 80 detailed
```

`packet-tracer`는 실제 패킷을 보내지 않고 라우팅·NAT·ACL·검사 단계를 통과시키며 어느 단계에서 drop되는지 보여준다. `show access-list`의 hitcnt가 증가하지 않으면 패킷이 해당 ACE에 도달하지 않았거나 주소·인터페이스·방향을 잘못 선택했을 가능성이 있다.

## 130. WebTerm·GNS3 — 공식 보강 본문

> GNS3의 ASAv, Docker 기반 WebTerm, IOS 라우터는 서로 다른 실행 모델을 사용한다. 장비가 화면에 배치되어 있다는 사실보다, 실제 링크·주소·게이트웨이·라우팅·서비스 포트가 이어지는지를 확인해야 한다.

### 1. ASAv와 GNS3 실행 모델

- ASA는 하드웨어 방화벽 제품군이고 ASAv는 같은 ASA 계열 기능을 가상 머신·가상 네트워크 환경에서 실행하는 형태다.
- GNS3 Docker 노드는 컨테이너 이미지와 호스트 커널을 공유하므로 가볍고 빠르지만, 컨테이너 내부에서 직접 넣은 주소·라우트가 이미지 재생성 뒤에도 남는다고 보장할 수 없다.
- GNS3 Cloud는 호스트의 Ethernet·TAP·UDP 같은 연결을 가상 토폴로지에 브리지하는 기능이다. Docker bridge와 Cloud 연결은 서로 다른 경로이므로, 어느 인터페이스가 실제 호스트망에 붙었는지 확인한다.

### 2. ASAv·WebTerm 템플릿과 토폴로지 확인

ASAv 템플릿은 선택한 ASAv 이미지·GNS3 VM·인터페이스 수에 의존한다. WebTerm은 GNS3 공식 Docker 템플릿 또는 프로젝트에서 지정한 Docker 이미지에 의존한다. 이미지가 다르면 `eth0` 이름, 기본 주소, 기본 gateway, 패키지 명령이 달라질 수 있다.

토폴로지를 열면 먼저 다음을 기록한다.

- WebTerm-1이 어느 ASA 인터페이스와 같은 L2 세그먼트인지
- WebTerm-2가 어느 ASA 인터페이스와 같은 L2 세그먼트인지
- 각 장비의 실제 인터페이스 이름과 링크 상태
- ASA의 `inside`·`outside` 이름과 security level
- 외부에서 내부로 가는 경로와 반환 경로

### 3. WebTerm 임시 IP·게이트웨이 설정

첨부 실습의 주소 계획은 다음과 같다.

- WebTerm-1: `192.168.100.200/24`, gateway `192.168.100.254`
- WebTerm-2: `192.168.200.100/24`, gateway `192.168.200.254`

컨테이너 내부에서 현재 주소를 먼저 보고, 중복 주소를 피하려면 `add` 대신 `replace`를 사용한다.

```bash
root@webterm-1:~# ip addr replace 192.168.100.200/24 dev eth0
root@webterm-1:~# ip link set dev eth0 up
root@webterm-1:~# ip route replace default via 192.168.100.254 dev eth0
root@webterm-1:~# ip addr show dev eth0
root@webterm-1:~# ip route
root@webterm-1:~# ping -c 3 192.168.100.254

root@webterm-2:~# ip addr replace 192.168.200.100/24 dev eth0
root@webterm-2:~# ip link set dev eth0 up
root@webterm-2:~# ip route replace default via 192.168.200.254 dev eth0
root@webterm-2:~# ip addr show dev eth0
root@webterm-2:~# ip route
root@webterm-2:~# ping -c 3 192.168.200.254
```

필기의 WebTerm-1은 먼저 `192.168.200.254`를 default gateway로 넣으려다 `Nexthop has invalid gateway`를 받았다. `192.168.100.200/24`를 eth0에 넣으면 커널은 `192.168.100.0/24`를 직접 연결망으로 본다. `192.168.200.254`는 그 L2 직접 연결망 밖이므로 일반적인 default route의 gateway로 검증되지 않는다. 같은 서브넷의 `192.168.100.254`로 고친 것은 이 오류에 맞는 해결이다.

단, `.254`가 항상 정답인 것은 아니다. Docker user-defined bridge는 네트워크 생성 시 gateway가 정해지고, 여러 네트워크에 붙은 컨테이너는 Docker가 default gateway를 선택할 수 있다. 실제 gateway가 다르면 `ip route`와 Docker 네트워크 설정을 확인하고 그 주소를 사용한다. 존재하지 않는 gateway를 `onlink` 옵션으로 억지로 등록하는 것은 정상적인 연결 복구가 아니다.

### 4. ping·HTTP·Telnet을 분리해서 시험하기

`ping`은 ICMP 응답 여부만 확인한다. ping 성공은 TCP 80/443 서비스가 열려 있다는 뜻이 아니며, HTTP가 실패해도 ICMP만 허용된 상태일 수 있다.

```bash
root@webterm-2:~# ip route get 192.168.100.200
root@webterm-2:~# ping -c 3 192.168.100.200
root@webterm-2:~# curl -v --connect-timeout 3 http://192.168.100.200/
root@webterm-2:~# nc -vz -w 3 192.168.100.200 80
```

연결 timeout은 경로·방화벽 drop·반환 경로 문제 가능성이 있고, connection refused는 목적지까지 도달했지만 해당 포트에 리스너가 없을 가능성이 크다. HTTP 상태 코드가 돌아오면 네트워크 경로와 TCP 접속은 통과한 것이다.

### 5. OSPF와 WebTerm 주소의 연결

OSPF는 주소 설정을 대신하지 않는다. 먼저 각 링크의 직접 연결 ping과 `show ip route`/`ip route`를 확인한 뒤, IOS와 ASA의 OSPF network 문법 차이를 적용한다. ASA는 일반 서브넷 마스크, IOS는 와일드카드 마스크를 사용한다. OSPF 인접성이 올라와도 ASA ACL·security level·서비스 포트가 별도로 허용되어야 최종 HTTP가 성공한다.

### 6. 영구 설정의 범위

`ip addr`, `ip route`로 넣은 값은 보통 현재 Linux 네임스페이스의 runtime 설정이다. 컨테이너가 재시작·재생성되면 사라질 수 있다. `/etc/network/interfaces.d/`에 파일을 만든다고 항상 적용되는 것도 아니다. 해당 이미지가 ifupdown을 읽는지, NetworkManager·systemd-networkd·자체 entrypoint를 쓰는지 확인한 뒤 재시작 테스트를 한다.

VPCS의 `save`는 VPCS 설정 저장 기능이지 Linux WebTerm 컨테이너의 설정을 영구화하는 명령이 아니다. 재현 가능한 실습은 Docker image/template의 entrypoint, GNS3 프로젝트 설정, 또는 별도의 초기화 스크립트로 관리한다.

### 7. 통합 확인 순서

1. GNS3 링크와 인터페이스가 up인지 확인한다.
2. WebTerm은 `ip addr`, `ip route`; Cisco 장비는 `show ip interface brief`, `show ip route`; ASA는 `show nameif`, `show interface ip brief`를 본다.
3. 같은 L2 구간의 gateway를 ping한다.
4. 목적지까지의 route를 확인한다.
5. `curl` 또는 `nc`로 실제 TCP 서비스 포트를 시험한다.
6. IOS ZPF는 zone-pair·policy-map·세션, ASA는 access-list·access-group·service-policy·packet-tracer를 확인한다.
7. 마지막으로 관리 plane인지 transit plane인지 다시 구분한다.
## 8. 필기 내용 정정 요약

1. **ZPF zone-pair만으로는 허용되지 않는다.** 반드시 service-policy를 연결하고, 시작 방향마다 정책을 설계한다.
2. **ZPF의 ACL과 ASA의 interface ACL을 같은 의미로 읽지 않는다.** ZPF class-map의 ACL은 분류 조건이고, policy-map의 inspect/pass/drop이 동작을 정한다.
3. **`permit ip any any`는 검증용 광범위 조건이다.** 운영 정책은 필요한 프로토콜·호스트·포트로 줄인다.
4. **ASA의 `passwd`는 Telnet용이다.** SSH·ASDM은 `username`과 `aaa authentication ... LOCAL`을 사용한다.
5. **ASA의 `http server enable`은 기본 HTTPS/ASDM 접속을 위한 명령이다.** IOS의 `ip http server`와 구별한다.
6. **ASA extended ACL은 출발지와 목적지를 모두 가져야 한다.** `permit any any`가 아니라 필요하면 `permit ip any any`지만 매우 위험하다.
7. **security-level의 high→low implicit permit은 transit의 기본 규칙일 뿐이다.** ACL·NAT·라우팅·서비스·ICMP 상태 처리가 별도로 남는다.
8. **WebTerm gateway는 주소와 같은 직접 연결 서브넷에 있어야 한다.** 오류 메시지는 라우팅 명령이 아니라 L2 도달 가능성 검증에서 발생한 것이다.
9. **`ip addr`·`ip route`는 컨테이너 runtime 설정이다.** 영구 설정은 이미지·entrypoint·GNS3 템플릿에 따라 따로 검증한다.
10. **`timetest`/`testtime` 오타를 통일한다.** 시간 범위는 이름과 유효 시간대까지 검증한다.

## 9. 공식 출처 (확인일: 2026-09-01)

- [Cisco IOS XE Zone-Based Policy Firewall Configuration Guide](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/sec_data_zbf/configuration/sec-data-zbf-xe-16-11-book/sec-zone-pol-fw.html)
- [Cisco Zone-Based Policy Firewall Design Guide](https://www.cisco.com/c/en/us/support/docs/security/ios-firewall/98628-zone-design-guide.html)
- [Cisco Secure Firewall ASA Access Rules](https://www.cisco.com/c/en/us/td/docs/security/asa/asa918/configuration/firewall/asa-918-firewall-config/access-rules.html)
- [Cisco Secure Firewall ASA Management Access](https://www.cisco.com/c/en/us/td/docs/security/asa/asa919/configuration/general/asa-919-general-config/admin-management.html)
- [Cisco ASA Access Control List Configuration Examples](https://www.cisco.com/c/en/us/support/docs/security/adaptive-security-appliance-asa-software/217679-asa-access-control-list-configuration-ex.html)
- [Cisco IOS HTTP 1.1 Web Server and Client](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/https/configuration/xe-17/https-xe-17-book/HTTP_1-1_Web_Server_and_Client.html)
- [Cisco ASA OSPF command reference](https://www.cisco.com/c/en/us/td/docs/security/asa/asa-cli-reference/I-R/asa-command-ref-I-R/ret-rz-commands.html)
- [Docker networking overview](https://docs.docker.com/engine/network/)
- [Docker bridge network driver](https://docs.docker.com/engine/network/drivers/bridge/)
- [GNS3 Docker template](https://docs.gns3.com/docs-3.1-en/web-ui/template-preferences-docker)
- [GNS3 Cloud template](https://docs.gns3.com/docs-3.1-en/web-ui/template-preferences-builtin)

