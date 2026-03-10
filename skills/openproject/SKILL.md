# OpenProject Skill

이 스킬은 OpenProject 운영 작업을 더 안정적으로 수행하기 위한 지침입니다.

## 조회

1. 프로젝트를 찾을 때는 먼저 `openproject_list_projects`를 사용합니다.
2. 작업을 찾을 때는 `openproject_list_work_packages`로 좁히고, 필요한 경우에만 `openproject_get_work_package`를 호출합니다.
3. 코멘트 이력은 `openproject_list_work_package_activities`로 최소 개수만 가져옵니다.

## 변경

1. 작업 생성 전에는 프로젝트, 타입, 우선순위, 담당자를 먼저 확인합니다.
2. 작업 수정 전에는 현재 work package 를 조회해서 대상이 맞는지 확인합니다.
3. 코멘트/수정/생성은 사용자의 의도가 명확할 때만 수행합니다.

## 컨텍스트 관리

1. 긴 설명이나 코멘트는 그대로 반복하지 말고 핵심만 요약합니다.
2. 프로젝트 ID, 작업 ID, 상태, 담당자, 마감일 위주로 맥락을 유지합니다.
3. 결과가 많으면 limit 를 줄이고 재질문합니다.

