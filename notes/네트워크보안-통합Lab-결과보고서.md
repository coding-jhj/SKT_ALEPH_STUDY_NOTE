# 네트워크 보안 기초 통합 Lab 결과보고서

라우팅·HSRP·ACL 구성 및 역할별 검증 결과. 팀 실습 보고서(`kload.pdf`)를 옮긴 것입니다.
원본이 이미지 PDF라 페이지를 렌더링해 읽고 표·명령·판정을 그대로 정리했습니다.

## 실습 목표

1. EIGRP·OSPF·GRE·VLAN으로 구성된 본사·지사 경로 확인
2. HSRP Active/Standby 역할과 VIP 상태 확인
3. ACL에서 FTP·WEB·ICMP 트래픽을 정책대로 허용·차단하는지 검증

## 역할 분담

| 담당 | 담당 작업 | 검증 결과 |
|---|---|---|
| 송우진 | 전체 토폴로지, G·D 통신 테스트, ACL 설정 확인 | G → C-S 성공 / D → F 차단 |
| 변준혁 | HSRP 토폴로지, A1·A2 상태 확인 | Active 105 / Standby 100 / VIP 공유 |
| 하태형 | G WEB, A FTP 허용·차단 테스트 | WEB 차단 / 내부 FTP 허용 / 외부 FTP 차단 |

## 검증 절차

| 단계 | 수행 내용 | 판정 자료 |
|---|---|---|
| 1. 구성 확인 | 주소·라우팅·터널·VLAN·게이트웨이 구조 확인 | 담당자별 토폴로지 |
| 2. 상태 확인 | HSRP 우선순위와 Active/Standby 상태 비교 | `show standby brief` |
| 3. 정책 검증 | 허용 경로와 차단 경로를 서비스별 실행 | ping·WEB·FTP 결과 |

---

## 1. 구성·통신 검증

전체 토폴로지는 **EIGRP AS 100**, **OSPF Area 0**, **GRE**, **HSRP**, **VLAN**으로
본사·지사를 연결한 구성입니다. 허용 경로 `G → C-S`와 차단 경로 `D → F`를 비교했습니다.

| 테스트 목적 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|
| G → C-S 종단 통신 | ping 응답 | Sent 4 / Received 4 / 0% loss | 통신 가능 |
| D → F ICMP 정책 | ping 차단 | Destination host unreachable / 100% loss | 정책과 일치 |

`D → F`는 `10.10.10.2`에서 **Destination host unreachable**이 반환되고 100% loss를 기록했습니다.
ACL의 ICMP echo deny 규칙과 결과가 일치하므로 차단 정책이 정상 동작했습니다.

> ⚠️ 처음 `ping 5.5.5.5`는 `Request timed out`이 섞여 2/4(50% loss)로 나왔고, 재시험에서
> 4/4·0% loss가 되었습니다. 첫 패킷 손실은 ARP·라우팅 수렴 대기 때문입니다.

## 2. ACL 설정 분석

라우터 실행 설정에서 확인한 부분입니다.

```
router ospf 1
 log-adjacency-changes
 network 5.5.5.0 0.0.0.255 area 0
 network 172.30.100.0 0.0.0.255 area 0
 network 10.10.10.0 0.0.0.255 area 0
!
ip nat inside source list 1 interface Serial0/3/0 overload
ip nat inside source static 172.30.100.2 5.5.5.5
ip classless
ip route 192.168.200.0 255.255.255.192 10.10.10.1
ip route 192.168.200.64 255.255.255.192 10.10.10.1
ip route 192.168.200.128 255.255.255.192 10.10.10.1
!
ip flow-export version 9
!
access-list 1 permit 172.30.100.0 0.0.0.255
access-list 100 permit ip host 5.5.5.2 host 4.4.4.1
access-list 110 deny tcp host 192.168.100.10 host 172.30.100.2 eq ftp
access-list 110 deny tcp host 192.168.100.10 host 5.5.5.5 eq ftp
access-list 110 deny tcp host 192.168.50.10 host 172.30.100.2 eq www
access-list 110 deny tcp host 192.168.50.10 host 5.5.5.5 eq www
access-list 110 deny icmp host 192.168.200.67 host 172.30.100.11 echo
access-list 110 permit ip any any
!
line con 0
line aux 0
!
line vty 0 4
 login
```

정책 표로 풀면 이렇습니다.

| 출발지 | 목적지·서비스 | 설정 의도 | 연결된 증빙 |
|---|---|---|---|
| A / 192.168.100.10 | 172.30.100.2 / 5.5.5.5 · FTP | 외부 FTP 차단 | 하태형 FTP 실패 |
| G / 192.168.50.10 | 172.30.100.2 / 5.5.5.5 · WEB | 외부 WEB 차단 | 하태형 Request Timeout |
| D / 192.168.200.67 | 172.30.100.11 / ICMP echo | D → F ping 차단 | 송우진 100% loss |
| 그 외 | `ip any any` | 나머지 IP 트래픽 허용 | 허용 경로와 함께 판단 |

**마지막 `permit ip any any`가 지정한 차단 규칙 외 IP 트래픽을 허용하는 정책 구조를 만듭니다.**
이 줄이 없으면 암묵적 `deny any`에 걸려 전부 막힙니다.

## 3. HSRP 이중화 검증

`192.168.100.0/24` 구간의 게이트웨이 이중화입니다. A1과 A2가 VIP `192.168.100.254`를 공유하고,
priority 차이로 Active·Standby 역할을 나눕니다.

```
A1#conf t
A1(config)#int gi0/0
A1(config-if)#do show standby brief
                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State    Active          Standby         Virtual IP
Gig0/0      1    105 P Active   local           192.168.100.2   192.168.100.254
```

```
A2#conf t
A2(config)#int gi0/0
A2(config-if)#do show standby brief
                     P indicates configured to preempt.
                     |
Interface   Grp  Pri P State    Active          Standby         Virtual IP
Gig0/0      1    100 P Standby  192.168.100.1   local           192.168.100.254
```

| 장비 | Priority | State | 상대 장비 | Virtual IP |
|---|---|---|---|---|
| A1 / Gig0/0 | 105 | Active | Standby 192.168.100.2 | 192.168.100.254 |
| A2 / Gig0/0 | 100 | Standby | Active 192.168.100.1 | 192.168.100.254 |

A1의 priority 105가 A2의 100보다 높아 A1이 Active, A2가 Standby입니다.
양쪽 `show standby brief` 결과가 서로를 가리키며 일치합니다.

## 4. WEB 정책 검증

| 출발지 → 목적지 | 서비스 | 기대 결과 | 실제 결과 |
|---|---|---|---|
| G → C-S / 5.5.5.5 | WEB | 차단 | Request Timeout |
| A → C-S / 5.5.5.5 | FTP | 차단 | Timed out |
| A → A-S / 192.168.100.20 | FTP | 허용 | Connected·FTP 배너 |

검증 방법을 명시적으로 남겼습니다.

| 항목 | 내용 |
|---|---|
| 출발지 | G / 192.168.50.10 |
| 목적지 | C-S 외부 매핑 주소 / 5.5.5.5 |
| 정책 근거 | ACL 110의 `G → 5.5.5.5 eq www deny` |
| 판정 | 브라우저 Request Timeout + ACL 설정 일치 → WEB 차단 |

## 5. FTP 허용·차단

출발지는 같고 **목적지와 정책만 다르므로** 허용·차단 차이를 직접 비교할 수 있는 구성입니다.

```
C:\>ftp 192.168.100.20
Trying to connect...192.168.100.20
Connected to 192.168.100.20
220- Welcome to PT Ftp server
Username:
```

```
C:\>ftp 5.5.5.5
Trying to connect...5.5.5.5

%Error opening ftp://5.5.5.5/ (Timed out)

(Disconnecting from ftp server)
```

| 목적지 | 기대 결과 | 실제 결과 | 판정 |
|---|---|---|---|
| A-S / 192.168.100.20 | FTP 허용 | Connected·220 배너 | 내부 FTP 정상 |
| C-S / 5.5.5.5 | FTP 차단 | Error opening ftp·Timed out | 외부 FTP 차단 |

## 종합 결론

1. **송우진** — G → C-S 최종 ping 4/4 응답, D → F ICMP 100% loss, ACL deny 규칙 확인
2. **변준혁** — A1 Active 105, A2 Standby 100, VIP 192.168.100.254 공유 확인
3. **하태형** — G WEB 차단, A 외부 FTP 차단, A 내부 FTP 허용 확인
4. 구성 화면·설정 내용·실행 결과가 역할별로 연결되어 실습 목표와 일치함

라우팅 통신, HSRP 상태, ACL 서비스 정책의 설정값과 실행 결과가 모두 일치하므로
실습 검증을 완료했습니다.

## 이 Lab에서 배울 점

**차단을 확인할 때 나오는 메시지가 곧 어디서 막혔는지 알려 줍니다.**

| 증상 | 어디서 막혔나 |
|---|---|
| `Destination host unreachable` | 라우터가 ICMP를 막고 응답을 돌려준 것 — ACL deny에 걸림 |
| `Request timed out` / `Timed out` | 응답이 아예 안 옴 — 조용히 버려졌거나 경로가 없음 |
| 브라우저 `Request Timeout` | TCP 세션이 성립하지 않음 — 포트 단위 차단 |

같은 "안 됨"이라도 메시지가 다르면 원인이 다릅니다. ACL로 막을 때
`deny`는 기본적으로 조용히 버리지만, 라우터가 unreachable을 돌려주는 경우도 있어
두 증상을 구분해서 읽어야 합니다.
