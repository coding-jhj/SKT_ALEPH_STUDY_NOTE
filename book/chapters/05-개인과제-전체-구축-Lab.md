# Cisco Packet Tracer 개인과제 — 처음부터 끝까지 완성 가이드

> **기준 자료:** 사용자가 제공한 과제 토폴로지 이미지  
> **목표:** 아무 설정도 되어 있지 않은 `.pkt` 파일이라고 가정하고, 이미지에 적힌 조건을 처음부터 순서대로 완성한다.  
> **주의:** 이미지에서 명시되지 않은 일부 라우터의 내부 IP는 토폴로지가 성립하도록 합리적으로 정한 값이다. 아래 표의 주소를 그대로 사용하면 된다. 인터페이스 번호는 이미지 기준이며, 실제 장비에서 다르면 `show ip interface brief`로 확인해서 해당 케이블이 꽂힌 인터페이스에 적용한다.

---

# 0. 과제에서 요구하는 것

이미지에 적힌 요구사항은 다음과 같다.

## 전체 요구사항

1. **모든 노드 통신 가능**
2. **EIGRP AS 100 설정**
3. **OSPF Area 0 설정**
4. EIGRP 영역과 OSPF 영역 사이도 서로 통신 가능하도록 **재분배(Redistribution)**
5. `192.168.100.0/24` 구간에 **HSRP 설정**
6. SKT 본사 `192.168.200.0/24`를 **최소 3개 VLAN으로 분할**
7. SKT 지사에 **DHCP 설정**
8. SKT 지사에 **NAT 설정**
9. C-S 서버 `172.30.100.12`를 **5.5.5.5로 Static NAT Mapping**
10. **ACL**
    - A → C-S : FTP 접속 불가능
    - 그 외 다른 노드 → C-S : FTP 접속 가능
    - G → C-S : WEB 접속 불가능
    - D → F : Ping 불가능
    - 그 외 모든 트래픽 허용
11. SKT 본사 ↔ SKT 지사 **Site-to-Site VPN**
12. 최종적으로 전체 통신 및 ACL/VPN/NAT 동작 확인

---

# 1. 장비 이름을 먼저 정하자

설명을 쉽게 하기 위해 라우터를 왼쪽부터 다음처럼 부른다.

| 이름 | 위치 | 역할 |
|---|---|---|
| R1 | 왼쪽 위 | EIGRP 라우터 / HSRP Active 후보 |
| R2 | 왼쪽 아래 | EIGRP 라우터 / HSRP Standby 후보 |
| R3 | 가운데 | EIGRP ↔ OSPF 경계 라우터 |
| R4 | SKT 본사 | OSPF / VLAN Router-on-a-Stick / VPN |
| R5 | 본사 위쪽 | OSPF 중계 라우터 |
| R6 | SKT 지사 | OSPF / DHCP / NAT / ACL / VPN |
| L3-SW | 가장 왼쪽 L3 스위치 | 192.168.50.0/24 게이트웨이 |
| SW-A | A/A-S가 연결된 스위치 | 192.168.100.0/24 |
| HQ-SW1 | SKT 본사 왼쪽 스위치 | VLAN 10/20/30 |
| HQ-SW2 | SKT 본사 오른쪽 스위치 | VLAN 10/20/30 |
| BR-SW | SKT 지사 스위치 | 172.30.100.0/24 |

---

# 2. 전체 IP 주소 계획

## 2-1. 왼쪽 LAN

### G

- IP: `192.168.50.10`
- Mask: `255.255.255.0`
- Gateway: `192.168.50.1`

### L3-SW

- VLAN 1 SVI: `192.168.50.1/24`
- R1과 연결되는 Routed Port: `6.6.6.2/24`

### R1

- G0/0: `6.6.6.1/24`
- G0/1: `192.168.100.2/24`
- S0/3/0: `1.1.1.1/24`

### R2

- G0/0: `192.168.100.3/24`
- S0/3/1: `2.2.2.2/24`

### HSRP Virtual Gateway

- `192.168.100.1`

### A

- IP: `192.168.100.10`
- Mask: `255.255.255.0`
- Gateway: `192.168.100.1`

### A-S

- IP: `192.168.100.20`
- Mask: `255.255.255.0`
- Gateway: `192.168.100.1`

---

## 2-2. EIGRP ↔ OSPF 경계

### R3

- S0/3/0: `1.1.1.2/24`
- S0/3/1: `2.2.2.1/24`
- S0/2/0: `3.3.3.1/24`

### R4 — SKT 본사

- S0/3/0: `3.3.3.2/24`
- S0/3/1: `4.4.4.1/24`
- G0/0: 물리 IP 없음, VLAN trunk 용도

### R5

- S0/3/1: `4.4.4.2/24`
- S0/3/0: `5.5.5.1/24`

### R6 — SKT 지사

- S0/3/0: `5.5.5.2/24`
- G0/0: `172.30.100.1/24`

---

# 3. SKT 본사 VLAN 주소 계획

원래 네트워크:

`192.168.200.0/24`

과제 이미지에는 `/26`으로 나누라고 되어 있다.

`/26 = 255.255.255.192`

한 서브넷은 64개씩 증가한다.

| VLAN | 이름 | Network | Gateway | 사용 가능한 주소 | Broadcast |
|---|---|---|---|---|---|
| 10 | banana | 192.168.200.0/26 | 192.168.200.1 | .1 ~ .62 | .63 |
| 20 | watermelon | 192.168.200.64/26 | 192.168.200.65 | .65 ~ .126 | .127 |
| 30 | apple | 192.168.200.128/26 | 192.168.200.129 | .129 ~ .190 | .191 |

남는 `192.168.200.192/26`은 이번 과제에서는 사용하지 않아도 된다.

## 본사 단말 주소

### C — VLAN 10

- IP: `192.168.200.10`
- Mask: `255.255.255.192`
- Gateway: `192.168.200.1`

### B — VLAN 20

- IP: `192.168.200.70`
- Mask: `255.255.255.192`
- Gateway: `192.168.200.65`

### D — VLAN 20

- IP: `192.168.200.80`
- Mask: `255.255.255.192`
- Gateway: `192.168.200.65`

### B-S — VLAN 30

- IP: `192.168.200.130`
- Mask: `255.255.255.192`
- Gateway: `192.168.200.129`

### E — VLAN 30

- IP: `192.168.200.140`
- Mask: `255.255.255.192`
- Gateway: `192.168.200.129`

---

# 4. SKT 지사 주소

## R6

G0/0:

- `172.30.100.1/24`

## F

이미지 기준:

- IP: `172.30.100.11`
- Mask: `255.255.255.0`
- Gateway: `172.30.100.1`

F는 DHCP 실습 대상이라면 나중에 `DHCP`로 변경한다.

## C-S

- IP: `172.30.100.12`
- Mask: `255.255.255.0`
- Gateway: `172.30.100.1`

C-S는 FTP/WEB 서버이므로 **Static IP**로 둔다.

---

# 5. 작업 순서

이 과제는 아래 순서로 해야 덜 꼬인다.

1. PC/Server IP
2. 각 Router interface IP
3. L3 Switch
4. HSRP
5. 본사 VLAN
6. Router-on-a-Stick
7. EIGRP
8. OSPF
9. EIGRP ↔ OSPF Redistribution
10. 전체 Ping
11. DHCP
12. NAT / Static NAT
13. C-S FTP/HTTP
14. ACL
15. VPN
16. 최종 검증
17. 설정 저장

**중요:** ACL과 VPN은 기본 통신이 완전히 된 후 가장 마지막에 한다.

---

# 6. Serial에서 꼭 알아야 할 것

Serial 연결의 한쪽은 DCE이고 다른 쪽은 DTE이다.

DCE 쪽에서만 다음 명령이 필요하다.

```cisco
clock rate 64000
```

어느 쪽이 DCE인지 확인:

```cisco
show controllers serial 0/3/0
```

출력에 `DCE`가 있는 라우터에서만 `clock rate 64000`을 입력한다.

이미지와 실제 Packet Tracer 장비의 DCE 방향이 다를 수 있으므로 무조건 양쪽에 넣지 말고 확인한다.

---

# 7. R1 설정

R1을 클릭 → CLI.

```cisco
enable
configure terminal
hostname R1
```

## G0/0 — L3-SW 방향

```cisco
interface gigabitEthernet0/0
ip address 6.6.6.1 255.255.255.0
no shutdown
exit
```

## G0/1 — 192.168.100.0 LAN

```cisco
interface gigabitEthernet0/1
ip address 192.168.100.2 255.255.255.0
no shutdown
exit
```

## Serial — R3 방향

```cisco
interface serial0/3/0
ip address 1.1.1.1 255.255.255.0
no shutdown
exit
```

DCE라면:

```cisco
interface serial0/3/0
clock rate 64000
exit
```

확인:

```cisco
end
show ip interface brief
```

---

# 8. R2 설정

```cisco
enable
configure terminal
hostname R2
```

## LAN

```cisco
interface gigabitEthernet0/0
ip address 192.168.100.3 255.255.255.0
no shutdown
exit
```

## R3 방향

```cisco
interface serial0/3/1
ip address 2.2.2.2 255.255.255.0
no shutdown
exit
```

DCE라면:

```cisco
interface serial0/3/1
clock rate 64000
exit
```

```cisco
end
show ip interface brief
```

---

# 9. L3-SW 설정

이 장비가 G의 Gateway `192.168.50.1` 역할을 한다.

## IP Routing 활성화

```cisco
enable
configure terminal
hostname L3-SW
ip routing
```

## VLAN 1 SVI

```cisco
interface vlan 1
ip address 192.168.50.1 255.255.255.0
no shutdown
exit
```

## R1로 가는 포트를 Layer 3 포트로 변경

이미지에서는 Fa0/2로 보인다.

```cisco
interface fastEthernet0/2
no switchport
ip address 6.6.6.2 255.255.255.0
no shutdown
exit
```

```cisco
end
show ip interface brief
```

G와 연결된 L2 access switch는 특별한 설정 없이 기본 VLAN 1로 사용해도 된다.

---

# 10. HSRP 설정

A와 A-S의 Gateway는 `192.168.100.1`이다.

그런데 실제 R1은 `.2`, R2는 `.3`을 사용한다.

`192.168.100.1`은 두 라우터가 공유하는 **가상 게이트웨이**가 된다.

## R1 — Active 우선

```cisco
R1# configure terminal
interface gigabitEthernet0/1
standby 1 ip 192.168.100.1
standby 1 priority 110
standby 1 preempt
exit
end
```

## R2 — Standby

```cisco
R2# configure terminal
interface gigabitEthernet0/0
standby 1 ip 192.168.100.1
standby 1 priority 100
standby 1 preempt
exit
end
```

확인:

```cisco
show standby brief
```

정상이라면:

- R1 → Active
- R2 → Standby
- Virtual IP → `192.168.100.1`

A와 A-S의 Default Gateway는 반드시:

```text
192.168.100.1
```

---

# 11. R3 설정

R3는 가장 중요한 **경계 라우터**이다.

왼쪽에서는 EIGRP를 사용하고 오른쪽에서는 OSPF를 사용한다.

```cisco
enable
configure terminal
hostname R3
```

## R1 방향

```cisco
interface serial0/3/0
ip address 1.1.1.2 255.255.255.0
no shutdown
exit
```

## R2 방향

```cisco
interface serial0/3/1
ip address 2.2.2.1 255.255.255.0
no shutdown
exit
```

## R4 방향

```cisco
interface serial0/2/0
ip address 3.3.3.1 255.255.255.0
no shutdown
exit
```

DCE인 Serial interface에만:

```cisco
clock rate 64000
```

확인:

```cisco
end
show ip interface brief
```

---

# 12. R4 — SKT 본사 라우터 기본 설정

```cisco
enable
configure terminal
hostname R4-HQ
```

## R3 방향

```cisco
interface serial0/3/0
ip address 3.3.3.2 255.255.255.0
no shutdown
exit
```

## R5 방향

```cisco
interface serial0/3/1
ip address 4.4.4.1 255.255.255.0
no shutdown
exit
```

## G0/0

G0/0에는 직접 IP를 넣지 않는다.

VLAN 10/20/30을 위한 Router-on-a-Stick을 사용하기 때문이다.

```cisco
interface gigabitEthernet0/0
no shutdown
exit
```

---

# 13. R5 설정

```cisco
enable
configure terminal
hostname R5
```

## R4 방향

```cisco
interface serial0/3/1
ip address 4.4.4.2 255.255.255.0
no shutdown
exit
```

## R6 방향

```cisco
interface serial0/3/0
ip address 5.5.5.1 255.255.255.0
no shutdown
exit
```

DCE인 경우:

```cisco
clock rate 64000
```

---

# 14. R6 — SKT 지사 기본 설정

```cisco
enable
configure terminal
hostname R6-BRANCH
```

## R5 방향

```cisco
interface serial0/3/0
ip address 5.5.5.2 255.255.255.0
no shutdown
exit
```

## 지사 LAN

```cisco
interface gigabitEthernet0/0
ip address 172.30.100.1 255.255.255.0
no shutdown
exit
```

---

# 15. SKT 본사 VLAN 생성

두 스위치 모두 VLAN 10, 20, 30을 만든다.

## HQ-SW1

```cisco
enable
configure terminal
hostname HQ-SW1

vlan 10
name banana
exit

vlan 20
name watermelon
exit

vlan 30
name apple
exit
```

## HQ-SW2

동일하게:

```cisco
enable
configure terminal
hostname HQ-SW2

vlan 10
name banana
exit

vlan 20
name watermelon
exit

vlan 30
name apple
exit
```

확인:

```cisco
show vlan brief
```

---

# 16. HQ-SW1 포트 VLAN 설정

이미지 기준:

- Fa0/2 → B → VLAN 20
- Fa0/3 → B-S → VLAN 30
- Fa0/1 → HQ-SW2 → Trunk
- Fa0/4 → R4 → Trunk

## B

```cisco
interface fastEthernet0/2
switchport mode access
switchport access vlan 20
exit
```

## B-S

```cisco
interface fastEthernet0/3
switchport mode access
switchport access vlan 30
exit
```

## HQ-SW2 연결

```cisco
interface fastEthernet0/1
switchport mode trunk
switchport trunk allowed vlan 10,20,30
exit
```

## R4 연결

```cisco
interface fastEthernet0/4
switchport mode trunk
switchport trunk allowed vlan 10,20,30
exit
```

---

# 17. HQ-SW2 포트 VLAN 설정

이미지 기준:

- Fa0/2 → E → VLAN 30
- Fa0/3 → D → VLAN 20
- Fa0/4 → C → VLAN 10
- Fa0/1 → HQ-SW1 → Trunk

```cisco
interface fastEthernet0/1
switchport mode trunk
switchport trunk allowed vlan 10,20,30
exit

interface fastEthernet0/2
switchport mode access
switchport access vlan 30
exit

interface fastEthernet0/3
switchport mode access
switchport access vlan 20
exit

interface fastEthernet0/4
switchport mode access
switchport access vlan 10
exit

end
```

확인:

```cisco
show vlan brief
show interfaces trunk
```

---

# 18. Router-on-a-Stick 설정

R4에서 VLAN별 Gateway를 만든다.

## 중요

G0/0 물리 interface에는 IP를 넣지 않는다.

```cisco
R4-HQ# configure terminal
```

## VLAN 10

```cisco
interface gigabitEthernet0/0.10
encapsulation dot1Q 10
ip address 192.168.200.1 255.255.255.192
exit
```

## VLAN 20

```cisco
interface gigabitEthernet0/0.20
encapsulation dot1Q 20
ip address 192.168.200.65 255.255.255.192
exit
```

## VLAN 30

```cisco
interface gigabitEthernet0/0.30
encapsulation dot1Q 30
ip address 192.168.200.129 255.255.255.192
exit
```

물리 interface:

```cisco
interface gigabitEthernet0/0
no shutdown
exit
end
```

확인:

```cisco
show ip interface brief
```

정상 예:

```text
GigabitEthernet0/0        unassigned          up   up
GigabitEthernet0/0.10     192.168.200.1       up   up
GigabitEthernet0/0.20     192.168.200.65      up   up
GigabitEthernet0/0.30     192.168.200.129     up   up
```

---

# 19. VLAN 내부 통신 먼저 확인

아직 라우팅 프로토콜을 넣기 전이라도 R4에 직접 연결된 VLAN끼리는 통신 가능해야 한다.

C에서:

```text
ping 192.168.200.65
ping 192.168.200.70
ping 192.168.200.80
ping 192.168.200.130
ping 192.168.200.140
```

예를 들어 C → B:

```text
ping 192.168.200.70
```

성공해야 한다.

안 되면 OSPF 문제가 아니다.

다음을 먼저 확인:

```cisco
show vlan brief
show interfaces trunk
show ip interface brief
```

---

# 20. EIGRP AS 100

EIGRP 영역:

```text
192.168.50.0/24
6.6.6.0/24
192.168.100.0/24
1.1.1.0/24
2.2.2.0/24
```

## L3-SW

```cisco
configure terminal
router eigrp 100
network 192.168.50.0 0.0.0.255
network 6.6.6.0 0.0.0.255
no auto-summary
exit
end
```

## R1

```cisco
configure terminal
router eigrp 100
network 6.6.6.0 0.0.0.255
network 192.168.100.0 0.0.0.255
network 1.1.1.0 0.0.0.255
no auto-summary
exit
end
```

## R2

```cisco
configure terminal
router eigrp 100
network 192.168.100.0 0.0.0.255
network 2.2.2.0 0.0.0.255
no auto-summary
exit
end
```

## R3

```cisco
configure terminal
router eigrp 100
network 1.1.1.0 0.0.0.255
network 2.2.2.0 0.0.0.255
no auto-summary
exit
end
```

확인:

```cisco
show ip eigrp neighbors
show ip route
show ip protocols
```

정상적인 EIGRP 경로는 `D`로 표시된다.

---

# 21. OSPF Area 0

OSPF 영역:

```text
3.3.3.0/24
4.4.4.0/24
5.5.5.0/24
192.168.200.0/26
192.168.200.64/26
192.168.200.128/26
172.30.100.0/24
```

## R3

```cisco
configure terminal
router ospf 1
network 3.3.3.0 0.0.0.255 area 0
exit
end
```

## R4

```cisco
configure terminal
router ospf 1
network 3.3.3.0 0.0.0.255 area 0
network 4.4.4.0 0.0.0.255 area 0
network 192.168.200.0 0.0.0.63 area 0
network 192.168.200.64 0.0.0.63 area 0
network 192.168.200.128 0.0.0.63 area 0
exit
end
```

## R5

```cisco
configure terminal
router ospf 1
network 4.4.4.0 0.0.0.255 area 0
network 5.5.5.0 0.0.0.255 area 0
exit
end
```

## R6

```cisco
configure terminal
router ospf 1
network 5.5.5.0 0.0.0.255 area 0
network 172.30.100.0 0.0.0.255 area 0
exit
end
```

확인:

```cisco
show ip ospf neighbor
show ip route
show ip protocols
```

정상적인 OSPF 경로:

```text
O
```

---

# 22. EIGRP와 OSPF 재분배

여기가 매우 중요하다.

R3에서는:

- 왼쪽 → EIGRP 100
- 오른쪽 → OSPF 1

두 라우팅 프로토콜은 자동으로 서로의 경로를 알려주지 않는다.

그래서 R3에서 **양방향 Redistribution**을 한다.

## OSPF 경로를 EIGRP에 넣기

```cisco
R3# configure terminal
router eigrp 100
redistribute ospf 1 metric 10000 100 255 1 1500
exit
```

EIGRP 외부 경로에는 metric이 필요하다.

```text
10000 = bandwidth
100   = delay
255   = reliability
1     = load
1500  = MTU
```

## EIGRP 경로를 OSPF에 넣기

```cisco
router ospf 1
redistribute eigrp 100 subnets
exit
end
```

확인:

```cisco
show ip route
```

EIGRP 쪽에서는 OSPF에서 넘어온 경로가 보통:

```text
D EX
```

OSPF 쪽에서는 EIGRP에서 넘어온 경로가 보통:

```text
O E2
```

로 나타난다.

---

# 23. 이 시점에서 전체 Ping 테스트

**아직 ACL, NAT, VPN을 넣지 않는다.**

기본 네트워크부터 확인한다.

## A에서

```text
ping 192.168.50.10
ping 192.168.200.10
ping 172.30.100.11
ping 172.30.100.12
```

## G에서

```text
ping 192.168.100.10
ping 192.168.200.70
ping 172.30.100.12
```

## C에서

```text
ping 192.168.100.10
ping 192.168.50.10
ping 172.30.100.11
```

## F에서

```text
ping 192.168.200.10
ping 192.168.100.10
```

**이 단계에서는 전부 성공해야 한다.**

안 되면 ACL/VPN으로 넘어가지 않는다.

---

# 24. SKT 지사 DHCP

이미지에서 R6에 `DHCP / NAT`가 표시되어 있다.

C-S는 서버이므로 `.12`를 Static으로 유지하고, F를 DHCP로 받을 수 있게 만든다.

먼저 예약 주소 제외:

```cisco
R6-BRANCH# configure terminal

ip dhcp excluded-address 172.30.100.1 172.30.100.10
ip dhcp excluded-address 172.30.100.12
```

DHCP Pool:

```cisco
ip dhcp pool BRANCH
network 172.30.100.0 255.255.255.0
default-router 172.30.100.1
dns-server 8.8.8.8
exit
end
```

F:

```text
Desktop
→ IP Configuration
→ DHCP
```

첫 할당이면 이미지처럼 `172.30.100.11`을 받을 가능성이 높다.

확인:

```cisco
show ip dhcp binding
show ip dhcp pool
```

---

# 25. C-S 서버 설정

C-S:

```text
IP Address:      172.30.100.12
Subnet Mask:     255.255.255.0
Default Gateway: 172.30.100.1
```

## HTTP

C-S 클릭:

```text
Services
→ HTTP
→ HTTP: On
```

## FTP

```text
Services
→ FTP
→ FTP: On
```

FTP 테스트용 계정을 하나 만든다.

예:

```text
Username: cisco
Password: cisco
```

권한은 필요하면 Read / Write 등을 체크한다.

---

# 26. Static NAT — C-S를 5.5.5.5로 Mapping

과제 이미지:

```text
C-S → 5.5.5.5 Mapping
→ Static NAT 설정
```

즉:

```text
Inside Local  = 172.30.100.12
Inside Global = 5.5.5.5
```

R6에서:

## NAT Inside

```cisco
configure terminal
interface gigabitEthernet0/0
ip nat inside
exit
```

## NAT Outside

```cisco
interface serial0/3/0
ip nat outside
exit
```

## Static NAT

```cisco
ip nat inside source static 172.30.100.12 5.5.5.5
end
```

확인:

```cisco
show ip nat translations
show ip nat statistics
```

예상:

```text
Inside global  5.5.5.5
Inside local   172.30.100.12
```

외부 PC에서는 C-S를 다음 주소로 접근하도록 시험한다.

```text
5.5.5.5
```

---

# 27. PAT도 요구되는 경우

이미지의 `DHCP / NAT`가 단순 Static NAT뿐만 아니라 지사 일반 PC의 NAT까지 요구하는 것으로 해석될 수 있다.

그 경우 R6에서 PAT를 추가한다.

VPN을 고려하여 VPN 대상 트래픽은 NAT에서 제외한다.

```cisco
configure terminal

access-list 120 deny ip 172.30.100.0 0.0.0.255 192.168.200.0 0.0.0.255
access-list 120 permit ip 172.30.100.0 0.0.0.255 any

ip nat inside source list 120 interface serial0/3/0 overload

end
```

Static NAT는 그대로 유지:

```cisco
ip nat inside source static 172.30.100.12 5.5.5.5
```

---

# 28. NAT 먼저 테스트

A 또는 다른 외부 PC에서:

```text
ping 5.5.5.5
```

FTP:

```text
ftp 5.5.5.5
```

WEB:

```text
Desktop
→ Web Browser
→ http://5.5.5.5
```

ACL을 넣기 전에는 정상 접속되는 것이 좋다.

---

# 29. ACL 요구사항 정확히 정리

이미지의 ACL 규칙:

```text
A → C-S : FTP 접속 불가능
그 외 다른 노드는 C-S FTP 접속 가능

G → C-S : WEB 접속 불가능

D → F : Ping 불가능

그 외 모든 트래픽 허용
```

주소:

| 장비 | IP |
|---|---|
| A | 192.168.100.10 |
| G | 192.168.50.10 |
| D | 192.168.200.80 |
| F | 172.30.100.11 |
| C-S private | 172.30.100.12 |
| C-S NAT | 5.5.5.5 |

---

# 30. ACL 구현 방법

이 과제에서는 R6로 들어오는 트래픽을 한곳에서 제어하면 관리하기 쉽다.

외부 사용자가 C-S에 접근할 때 Static NAT 주소 `5.5.5.5`를 사용한다고 가정하고 R6 Serial 입구에서 필터링한다.

## R6 Extended ACL

```cisco
R6-BRANCH# configure terminal

ip access-list extended SECURITY
deny tcp host 192.168.100.10 host 5.5.5.5 eq 21
deny tcp host 192.168.50.10 host 5.5.5.5 eq 80
deny icmp host 192.168.200.80 host 172.30.100.11 echo
permit ip any any
exit
```

R5에서 들어오는 Serial에 적용:

```cisco
interface serial0/3/0
ip access-group SECURITY in
exit
end
```

확인:

```cisco
show access-lists
show ip interface serial0/3/0
```

---

# 31. 만약 교수님이 C-S의 내부 IP로 ACL을 검사한다면

Packet Tracer 실습에서 C-S 접근 주소를 `172.30.100.12`로 검사하도록 되어 있다면 위 두 줄의 목적지 주소만 바꾼다.

```cisco
deny tcp host 192.168.100.10 host 172.30.100.12 eq 21
deny tcp host 192.168.50.10 host 172.30.100.12 eq 80
```

즉 두 방식 중 **실제 과제 채점 시 사용하는 C-S 주소 기준**으로 선택한다.

이미지에 Static NAT `5.5.5.5 Mapping`이 명시되어 있으므로 우선은 `5.5.5.5` 접근을 기준으로 검사하는 것이 자연스럽다.

---

# 32. ACL 테스트

## A → C-S FTP

A:

```text
ftp 5.5.5.5
```

**실패해야 정상**

---

## 다른 노드 → C-S FTP

예: G:

```text
ftp 5.5.5.5
```

**성공해야 정상**

---

## G → C-S WEB

G Web Browser:

```text
http://5.5.5.5
```

**실패해야 정상**

---

## A 또는 다른 PC → C-S WEB

```text
http://5.5.5.5
```

**성공해야 정상**

---

## D → F Ping

D:

```text
ping 172.30.100.11
```

**실패해야 정상**

---

## C → F Ping

C:

```text
ping 172.30.100.11
```

**성공해야 정상**

---

# 33. ACL에서 `permit ip any any`가 반드시 필요한 이유

Cisco ACL에는 마지막에 보이지 않는 규칙이 있다.

```text
deny ip any any
```

이를 **Implicit Deny**라고 한다.

따라서 문제에서:

> 그 외 모든 트래픽은 허용

이라고 했기 때문에 마지막에 반드시:

```cisco
permit ip any any
```

를 넣어야 한다.

---

# 34. Site-to-Site VPN

과제:

```text
SKT 본사 ↔ SKT 지사 Site-to-Site VPN
```

보호할 내부 네트워크:

```text
본사: 192.168.200.0/24
지사: 172.30.100.0/24
```

VPN Peer:

```text
R4 외부 주소: 4.4.4.1
R6 외부 주소: 5.5.5.2
```

R5는 단순 중계 라우터이며 VPN 종료점이 아니다.

---

# 35. R4 VPN 설정

## Interesting Traffic ACL

```cisco
R4-HQ# configure terminal

access-list 110 permit ip 192.168.200.0 0.0.0.255 172.30.100.0 0.0.0.255
```

## IKE Phase 1

```cisco
crypto isakmp policy 10
encr aes
hash sha
authentication pre-share
group 2
exit
```

Pre-shared Key:

```cisco
crypto isakmp key cisco123 address 5.5.5.2
```

## IPsec Transform Set

```cisco
crypto ipsec transform-set VPN-SET esp-aes esp-sha-hmac
```

## Crypto Map

```cisco
crypto map VPN-MAP 10 ipsec-isakmp
set peer 5.5.5.2
set transform-set VPN-SET
match address 110
exit
```

## 실제 외부 Interface에 적용

R5 방향은 S0/3/1:

```cisco
interface serial0/3/1
crypto map VPN-MAP
exit
end
```

---

# 36. R6 VPN 설정

반대 방향으로 정확히 대칭이어야 한다.

## Interesting Traffic ACL

```cisco
R6-BRANCH# configure terminal

access-list 110 permit ip 172.30.100.0 0.0.0.255 192.168.200.0 0.0.0.255
```

## IKE Phase 1

```cisco
crypto isakmp policy 10
encr aes
hash sha
authentication pre-share
group 2
exit
```

키와 알고리즘은 R4와 같아야 한다.

```cisco
crypto isakmp key cisco123 address 4.4.4.1
```

## Transform Set

```cisco
crypto ipsec transform-set VPN-SET esp-aes esp-sha-hmac
```

## Crypto Map

```cisco
crypto map VPN-MAP 10 ipsec-isakmp
set peer 4.4.4.1
set transform-set VPN-SET
match address 110
exit
```

## Serial에 적용

```cisco
interface serial0/3/0
crypto map VPN-MAP
exit
end
```

---

# 37. VPN 테스트

VPN은 설정만 한다고 바로 SA가 생기지 않을 수 있다.

**Interesting Traffic를 발생시켜야 한다.**

C에서:

```text
ping 172.30.100.11
```

또는 F에서:

```text
ping 192.168.200.10
```

첫 Ping은 VPN 협상 때문에 일부 실패할 수 있다.

다시 Ping한다.

R4/R6에서:

```cisco
show crypto isakmp sa
show crypto ipsec sa
```

정상이라면 ISAKMP SA가 잡히고 IPsec packet count가 증가한다.

특히:

```text
#pkts encaps
#pkts encrypt
#pkts decaps
#pkts decrypt
```

값이 증가하는지 본다.

---

# 38. VPN과 NAT가 충돌할 때

지사 R6에서 PAT를 설정했다면:

```text
172.30.100.0 → 192.168.200.0
```

VPN 트래픽이 NAT되지 않도록 해야 한다.

그래서 앞에서 만든 NAT ACL이:

```cisco
access-list 120 deny ip 172.30.100.0 0.0.0.255 192.168.200.0 0.0.0.255
access-list 120 permit ip 172.30.100.0 0.0.0.255 any
```

인 것이다.

의미:

```text
본사로 가는 트래픽 → NAT 하지 않음
그 외 → NAT 허용
```

---

# 39. 가장 중요한 최종 점검 순서

한꺼번에 검사하지 말고 아래 순서로 확인한다.

## ① Interface

모든 라우터:

```cisco
show ip interface brief
```

사용 중인 interface는 원칙적으로:

```text
up / up
```

이어야 한다.

---

## ② VLAN

HQ-SW1 / HQ-SW2:

```cisco
show vlan brief
```

확인:

- VLAN 10
- VLAN 20
- VLAN 30

---

## ③ Trunk

```cisco
show interfaces trunk
```

Trunk에 VLAN 10,20,30이 허용되어 있어야 한다.

---

## ④ HSRP

R1/R2:

```cisco
show standby brief
```

확인:

```text
R1 Active
R2 Standby
Virtual IP 192.168.100.1
```

---

## ⑤ EIGRP

```cisco
show ip eigrp neighbors
show ip protocols
```

AS:

```text
100
```

---

## ⑥ OSPF

```cisco
show ip ospf neighbor
show ip protocols
```

Neighbor 상태:

```text
FULL
```

---

## ⑦ Routing Table

```cisco
show ip route
```

확인할 코드:

```text
C     Connected
L     Local
D     EIGRP
D EX  EIGRP External
O     OSPF
O E2  OSPF External
```

---

## ⑧ DHCP

R6:

```cisco
show ip dhcp binding
show ip dhcp pool
```

---

## ⑨ NAT

```cisco
show ip nat translations
show ip nat statistics
```

특히:

```text
172.30.100.12 ↔ 5.5.5.5
```

---

## ⑩ ACL

```cisco
show access-lists
```

Packet counter가 올라가는지 확인한다.

---

## ⑪ VPN

```cisco
show crypto isakmp sa
show crypto ipsec sa
```

---

# 40. 최종 기능 시험표

| 시험 | 정상 결과 |
|---|---|
| A → G Ping | 성공 |
| A → C Ping | 성공 |
| A → F Ping | 성공 |
| G → D Ping | 성공 |
| C → F Ping | 성공 |
| E → A Ping | 성공 |
| A → C-S FTP | **실패** |
| G → C-S FTP | 성공 |
| G → C-S WEB | **실패** |
| A → C-S WEB | 성공 |
| D → F Ping | **실패** |
| C → F Ping | 성공 |
| C-S `5.5.5.5` Static NAT | 동작 |
| F DHCP | 주소 할당 |
| 본사 ↔ 지사 VPN | IPsec SA 생성 |

---

# 41. Ping이 안 될 때 확인 순서

다음 순서를 절대로 건너뛰지 않는다.

## 1단계 — 자기 Gateway

예: C

```text
ping 192.168.200.1
```

안 되면 VLAN 또는 Router-on-a-Stick 문제다.

---

## 2단계 — 바로 옆 Router

예:

R4:

```cisco
ping 3.3.3.1
ping 4.4.4.2
```

안 되면 Serial 설정 문제다.

---

## 3단계 — Routing Table

```cisco
show ip route
```

목적지 Network가 없는지 확인한다.

---

## 4단계 — Neighbor

EIGRP:

```cisco
show ip eigrp neighbors
```

OSPF:

```cisco
show ip ospf neighbor
```

---

## 5단계 — ACL

```cisco
show access-lists
```

ACL을 잘못 적용하면 정상 트래픽까지 막힐 수 있다.

필요하면 일시적으로:

```cisco
interface serial0/3/0
no ip access-group SECURITY in
```

로 ACL을 제거하고 기본 통신부터 다시 확인한다.

---

## 6단계 — VPN/NAT

기본 Routing이 되는 것을 확인한 후에만 NAT/VPN 문제를 본다.

---

# 42. 자주 발생하는 오류

## `overlaps with ...`

예:

```text
% 192.168.100.0 overlaps with GigabitEthernet0/0
```

같은 라우터의 다른 Layer 3 interface에 이미 같은 Network가 들어가 있다는 뜻이다.

```cisco
show ip interface brief
show running-config
```

로 확인한다.

---

## `administratively down`

`no shutdown`이 안 되어 있다.

```cisco
interface ...
no shutdown
```

---

## Serial `up/down`

물리 연결은 되어 있지만 Layer 2가 제대로 동작하지 않는 상태다.

확인:

- 양쪽 encapsulation
- DCE clock rate
- 케이블
- 반대쪽 no shutdown

---

## Serial `down/down`

물리 또는 반대쪽 interface 문제다.

---

## VLAN PC가 Gateway Ping 실패

확인:

```cisco
show vlan brief
show interfaces trunk
show ip interface brief
```

특히:

```text
PC Port VLAN
Switch Trunk
Router dot1Q
PC Subnet Mask
Gateway
```

다섯 가지를 본다.

---

# 43. 모든 설정 저장

각 Router/Switch에서 마지막에:

```cisco
copy running-config startup-config
```

또는:

```cisco
write memory
```

Packet Tracer 파일 자체도:

```text
File → Save
```

로 저장한다.

---

# 44. 과제 전체 구조를 한 번에 이해하기

이 토폴로지는 크게 3부분이다.

```text
[왼쪽 사내망]
192.168.50.0
192.168.100.0
      │
      │ EIGRP AS 100
      ▼
     R3
      │
      │ Redistribution
      ▼
   OSPF Area 0
      │
      ├── SKT 본사
      │   192.168.200.0/24
      │   VLAN 10 / 20 / 30
      │
      └── SKT 지사
          172.30.100.0/24
          DHCP / NAT / Server
```

추가 기능:

```text
192.168.100.0
→ HSRP

본사 VLAN
→ Router-on-a-Stick

EIGRP ↔ OSPF
→ Redistribution

C-S
172.30.100.12
↔
5.5.5.5
→ Static NAT

A / G / D
→ Extended ACL

본사 ↔ 지사
→ Site-to-Site IPsec VPN
```

---

# 45. 실제 수행할 때 가장 안전한 체크포인트

## 체크포인트 A — IP만 입력한 직후

바로 연결된 장비끼리 Ping.

## 체크포인트 B — VLAN 완료 후

본사 C/B/D/E/B-S끼리 서로 Ping.

## 체크포인트 C — EIGRP 완료 후

G ↔ A 통신.

## 체크포인트 D — OSPF 완료 후

C ↔ F 통신.

## 체크포인트 E — Redistribution 완료 후

A ↔ C, G ↔ F 등 전체 Ping.

**여기까지 모든 통신이 된 다음에만 보안 기능을 추가한다.**

## 체크포인트 F — DHCP/NAT

F DHCP 확인, C-S `5.5.5.5` 확인.

## 체크포인트 G — ACL

문제에서 막으라고 한 것만 정확히 막히는지 확인.

## 체크포인트 H — VPN

본사 ↔ 지사 트래픽으로 VPN SA 생성 확인.

---

# 46. 최종 명령어 요약

## 기본

```cisco
enable
configure terminal
show ip interface brief
show running-config
show ip route
```

## EIGRP

```cisco
router eigrp 100
network ...
no auto-summary
show ip eigrp neighbors
```

## OSPF

```cisco
router ospf 1
network ... area 0
show ip ospf neighbor
```

## Redistribution

```cisco
router eigrp 100
redistribute ospf 1 metric 10000 100 255 1 1500

router ospf 1
redistribute eigrp 100 subnets
```

## VLAN

```cisco
vlan 10
vlan 20
vlan 30

switchport mode access
switchport access vlan X

switchport mode trunk
```

## Router-on-a-Stick

```cisco
interface g0/0.10
encapsulation dot1Q 10
ip address ...

interface g0/0.20
encapsulation dot1Q 20
ip address ...

interface g0/0.30
encapsulation dot1Q 30
ip address ...
```

## HSRP

```cisco
standby 1 ip 192.168.100.1
standby 1 priority 110
standby 1 preempt
```

## DHCP

```cisco
ip dhcp excluded-address ...
ip dhcp pool ...
network ...
default-router ...
dns-server ...
```

## NAT

```cisco
ip nat inside
ip nat outside
ip nat inside source static 172.30.100.12 5.5.5.5
```

## ACL

```cisco
ip access-list extended SECURITY
deny ...
permit ip any any
```

## VPN

```cisco
crypto isakmp policy 10
crypto isakmp key ...
crypto ipsec transform-set ...
crypto map ...
```

---

# 47. 완료 기준

이 과제는 단순히 초록불이 들어오는 것으로 끝난 것이 아니다.

다음이 모두 만족되어야 완료다.

- 모든 사용 interface `up/up`
- VLAN 10/20/30 정상
- Inter-VLAN Routing 정상
- HSRP Active/Standby 정상
- EIGRP Neighbor 정상
- OSPF Neighbor FULL
- EIGRP ↔ OSPF 경로 재분배 정상
- 기본적으로 모든 노드 통신 가능
- F DHCP 정상
- C-S Static NAT `5.5.5.5` 정상
- A → C-S FTP만 차단
- G → C-S WEB만 차단
- D → F ICMP Echo만 차단
- 나머지 트래픽 허용
- 본사 ↔ 지사 VPN SA 정상
- `copy running-config startup-config` 완료
- Packet Tracer `.pkt` 파일 저장 완료

---

## 마지막 주의

이 문서는 제공된 이미지의 토폴로지와 과제 문구를 기준으로 작성했다.

이미지에서 명확히 적혀 있지 않은 R1/R2의 `192.168.100.2`, `192.168.100.3`, L3-SW의 `6.6.6.2` 같은 실제 interface 주소는 **HSRP 및 전체 라우팅이 정상 동작하도록 정한 주소**다. 이 주소 체계를 처음부터 그대로 적용하면 서로 충돌하지 않는다.

또한 Packet Tracer 장비 모델에 따라 Serial 번호가 `S0/2/0`, `S0/3/0`, `S0/3/1` 등 다를 수 있다. 그런 경우 **IP 주소와 연결 방향은 그대로 유지하고 실제 케이블이 꽂힌 interface 번호만 바꿔서 입력한다.**
