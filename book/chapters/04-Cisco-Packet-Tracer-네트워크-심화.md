# 네트워크·Cisco Packet Tracer

1부의 핵심 장입니다. 패킷이 호스트에서 목적지까지 이동하는 흐름을 먼저 이해한 뒤 IPv4·서브네팅, Cisco IOS CLI, 스위칭, 라우팅, DHCP·NAT·ACL, 게이트웨이 이중화, VPN, IPv6 순서로 확장합니다.

## 이 장에서 배우는 순서

1. 패킷 흐름과 계층별 장비·주소
2. IPv4 주소, 서브네팅, CIDR, VLSM
3. Cisco IOS CLI와 Packet Tracer 토폴로지 구성
4. 스위칭, VLAN, STP, Inter-VLAN Routing
5. 정적 라우팅, RIP, EIGRP, OSPF
6. DHCP, NAT/PAT, ACL
7. HSRP/FHRP 게이트웨이 이중화
8. GRE·IPsec VPN
9. IPv6, NDP, SLAAC, OSPFv3
10. 구성 검증, 장애 추적, 통합 Lab

## 연결 원고

### 기존 Cisco 실습 기록

- [라우팅·ACL·NAT·VPN 실습 원고](../../notes/2026-08-18_라우팅-ACL-NAT-VPN.md)

### 네트워크 개념·공식 기준 원고

- [네트워크·Cisco Packet Tracer 학습 원고](../../notes/2026-08-30_네트워크-Cisco-심화-공식보강.md)
- [공식 출처 목록](SOURCES.md)

## 실습 원칙

- 설정 전후에 `show running-config`, `show ip interface brief`, `show ip route`, `show vlan brief`, `show spanning-tree` 등 상태 확인 명령을 실행합니다.
- 장비 이미지·IOS 버전에 따라 지원 명령과 출력이 달라질 수 있으므로 결과를 그대로 기록합니다.
- ACL은 방향·인터페이스·처리 순서·암시적 deny를 함께 검토합니다.
- 보안·공격 실습은 승인된 대상과 격리된 네트워크에서만 실행하고, 실행 전 원복 계획을 적습니다.

## 책 이동

- [← 전체 책 목차](../README.md)
- [전체 순서표](../ORDER.md)
- [다음: 네트워크 핵심키워드 1 →](12-핵심키워드-네트워크-1.md)
