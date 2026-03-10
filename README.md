# Open2Deep

`Open2Deep`는 `deepagents` 기반의 on-prem CLI 에이전트이고, 기본 실행 명령은 `o2d`입니다. `open2deep` 별칭도 함께 제공합니다. 목적은 Codex처럼 아무 폴더에서나 실행하면서, OpenProject 작업을 더 깊은 컨텍스트와 함께 다루고 로컬 파일/셸/MCP/커스텀 툴까지 함께 쓰는 것입니다.

## 설치

```bash
pip install -e .
```

설치 후에는 현재 셸에서 `o2d` 또는 `open2deep` 명령을 바로 쓸 수 있습니다.

## 빠른 시작

전역 홈 초기화:

```bash
o2d init --global
```

현재 프로젝트용 로컬 초기화:

```bash
o2d init --project
```

대화형 실행:

```bash
o2d
```

한 번만 실행:

```bash
o2d 현재 폴더 구조와 할 일을 요약해줘
```

## 디렉터리 구조

전역 홈:

```text
~/.o2d/
  config.toml
  AGENTS_O2D.md
  PROMPT_O2D.md
  mcp_servers.json
  skills/
  tools/
```

프로젝트 로컬:

```text
./AGENTS_O2D.md
./.o2d/
  mcp_servers.json
  skills/
  tools/
```

## 로드 우선순위

- 메모리: `~/.o2d/AGENTS_O2D.md` -> `./AGENTS_O2D.md` -> `./.o2d/AGENTS_O2D.md` -> `./AGENTS.md`
- 스킬: `~/.o2d/skills/` -> `./.o2d/skills/` -> `./skills/`
- 커스텀 툴: `~/.o2d/tools/` -> `./.o2d/tools/` -> `./custom_tools/`
- MCP: `~/.o2d/mcp_servers.json` -> `./.o2d/mcp_servers.json` -> `./mcp_servers.json`

뒤에 오는 경로가 같은 이름을 override 하도록 설계했습니다.

추가로 이전 이름인 `ORDO_*`, `OPUS_*`, `AGENTS_ORDO.md`, `AGENTS_OPUS.md`, `PROMPT_ORDO.md`, `PROMPT_OPUS.md`, `./.ordo/`, `./.opus/`도 fallback 으로 계속 읽습니다.

## LLM 설정

환경변수 또는 `~/.o2d/config.toml` / `./.o2d/config.toml`로 설정할 수 있습니다.

대표 환경변수:

```bash
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://your-llm-endpoint/v1"
export OPENAI_MODEL="Qwen3-Coder-480B-A35B-Instruct"
export OPENAI_MODEL_VISION="Llama-4-Scout"
```

선택:

```bash
export O2D_CONTEXT_WINDOW=128000
export O2D_ENABLE_EXECUTE=1
export O2D_MAX_ITEMS=25
export O2D_MAX_TEXT_CHARS=1600
```

`OPENAI_APIK_KEY` 오타 변수와 이전 `ORDO_*`, `OPUS_*` 계열 변수도 fallback 으로 읽습니다.

## OpenProject 설정

OpenProject는 선택 기능입니다. 아래 값이 있으면 관련 툴이 자동으로 붙습니다.

```bash
export OPENPROJECT_BASE_URL="https://your-openproject.example.com"
export OPENPROJECT_API_KEY="your-api-token"
```

자동 로드되는 OpenProject 툴:

- `openproject_list_projects`
- `openproject_get_project`
- `openproject_list_project_types`
- `openproject_list_available_assignees`
- `openproject_list_statuses`
- `openproject_list_priorities`
- `openproject_list_work_packages`
- `openproject_get_work_package`
- `openproject_list_work_package_activities`
- `openproject_create_work_package`
- `openproject_update_work_package`
- `openproject_add_comment`

## 관리 명령

```bash
o2d tools
o2d mcp
o2d doctor
```

## 호환 스크립트

- `projects.py`
- `work_packages.py`
- `openproject_agent.py` (`o2d` 래퍼)

## 현재 제한

- 세션 상태는 현재 프로세스 안의 `thread_id` 기준으로만 유지됩니다.
- OpenProject 변경 작업은 실제로 수행되므로, 운영 환경에서는 `AGENTS_O2D.md`에 승인 규칙을 적어 두는 편이 안전합니다.
