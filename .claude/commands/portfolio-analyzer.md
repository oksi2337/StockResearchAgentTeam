---
description: 목표비중 스크린샷 + 보유현황 스크린샷을 분석해 조정필요금액·비중을 Excel로 정리합니다. 인자 1개면 기존 목표비중 사용.
argument-hint: [목표비중이미지] [보유현황이미지]
---

`portfolio-analyzer` 서브에이전트에 "$ARGUMENTS"를 위임하세요. Task tool을 `subagent_type="portfolio-analyzer"`로 호출하고, prompt에 `$ARGUMENTS`를 그대로 전달하세요. 인자가 없으면 기본 스크린샷 폴더(`C:\Users\kukuk\Pictures\Screenshots`)에서 이미지를 선택받습니다.
