# harness-server

เอเจนต์ AI สำหรับงานข่าวกรองจากแหล่งข้อมูลเปิด (OSINT) ที่สร้างบน [Hermes Agent](https://github.com/NousResearch/hermes-agent) พร้อมบุคลิก กฎการทำงาน และ skill นักวิเคราะห์ข่าวกรอง
ติดตั้งเป็น **profile ของ Hermes ชื่อ `osint`** ด้วยคำสั่งเดียว และให้บริการ API แบบ OpenAI-compatible แก่แอปอื่น โดยเชื่อมต่อเครื่องมือผ่าน MCP ได้แก่ Perplexity, ตรวจคำสะกดภาษาไทย และคลังความรู้ LightRAG

ผู้พัฒนา: **Chacharin Lertyosbordin**

> โปรเจกต์นี้คือการตั้งค่าและเนื้อหาของเอเจนต์ (SOUL และ skill) ที่ใช้กับ Hermes Agent ไม่ได้รวมตัว Hermes มาด้วย
> Hermes Agent พัฒนาโดย Nous Research ภายใต้สัญญาอนุญาต MIT และโปรเจกต์นี้ไม่ใช่ผลงานทางการของ Nous Research

## ภาพรวม

เอเจนต์ osint ทำงานได้ 2 แบบ

- **ผู้ช่วยทั่วไป** ตอบคำถามเป็นภาษาไทยและอังกฤษ ค้นเว็บ ถามตอบผ่าน Perplexity ใช้คลังความรู้ ตรวจคำสะกดภาษาไทย และบันทึกผลงานเป็นไฟล์
- **นักวิเคราะห์ข่าวกรอง** เมื่อสั่ง "ทำหน้าที่เป็นนักวิเคราะห์" เอเจนต์จะทำงาน 4 ขั้น (รวบรวมข้อมูล → ประเมินแหล่ง → วิเคราะห์ STEEPM → รายงานผู้บริหาร) ทีละขั้น เขียนผลแต่ละขั้นเป็นไฟล์ และรอคำสั่งก่อนขึ้นขั้นถัดไป

## สถาปัตยกรรม

### 3 ชั้นที่ประกอบกันเป็นระบบ

| ชั้น | มาจาก | ให้อะไร |
|---|---|---|
| **image ของ Hermes** | `nousresearch/hermes-agent:v0.21.6` (Docker Hub) | ตัวเอเจนต์ทั้งหมด: gateway และ API, dashboard, เครื่องมือในตัว (web_search, file, terminal, memory …), ระบบ skill, การเชื่อม MCP และระบบ profile |
| **profile osint** | repo นี้ ติดตั้งด้วย `hermes profile install` | ตัวตนของเอเจนต์: `SOUL.md`, skill `intelligence-analyzer` และ `config.yaml` (model, โฟลเดอร์ทำงาน, MCP) |
| **การติดตั้งของคุณ** | โฟลเดอร์ `data/` และ container อื่นใน docker network | ค่าลับ (`.env`), บทสนทนา, ความจำ, workspace และ MCP server ทั้ง 3 ตัว |

repo นี้จึงเล็กมาก (ราว 100 KB) เพราะไม่ได้รวมตัว Hermes มาด้วย อัปเดต Hermes ได้โดยเปลี่ยน image และอัปเดตเอเจนต์ได้ด้วย `hermes profile update` แยกจากกัน

### container และการเชื่อมต่อ

```
                                   docker network: agent_network
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                     │
│  แอปที่เรียกเอเจนต์ ──/p/osint/v1──▶ hermes (gateway เดียวของเครื่อง, พอร์ต 8642)           │
│                                    ├─ profile default                               │
│                                    └─ profile osint ◀── repo นี้                      │
│                                         │ MCP (HTTP)                                │
│                     ┌───────────────────┼────────────────────┐                      │
│                     ▼                   ▼                    ▼                      │
│             mcp-perplexity     mcp-thai-proofread       mcp-lightrag ──▶ LightRAG   │
│                                        │                                            │
│  ผู้ดูแลระบบ ──:9119──▶ hermes-dashboard │ mount โฟลเดอร์เดียวกัน                         │
└────────────────────────────────────────┼────────────────────────────────────────────┘
                                         ▼
                   data/workspace  (workspace กลาง: แฟ้มงานและรายงานของเอเจนต์)
```

- Hermes 0.21 ให้มี **gateway เพียงตัวเดียวต่อเครื่อง** คือ gateway ของ profile `default` ซึ่งให้บริการทุก profile ผ่าน path `/p/<profile>/` profile osint จึงไม่ต้องเปิด gateway ของตัวเอง แต่มี `API_SERVER_KEY` ของตัวเอง
- **MCP ทั้งสามตัวและแอปที่เรียก API แยกไปไว้เครื่องอื่นได้** mcp-thai-proofread ซึ่งต้องแก้ไฟล์ใน workspace จะอ่านและเขียนไฟล์ผ่าน API ไฟล์ของ dashboard ของ Hermes (`/api/files/…`) เมื่ออยู่คนละเครื่อง หรือ mount `data/workspace` โดยตรงเมื่ออยู่เครื่องเดียวกัน

### โฟลเดอร์ `data/` หลังติดตั้ง

```
data/
├── config.yaml, .env, auth.json      ← ของ profile default (gateway, dashboard และรหัสผ่าน dashboard)
├── profiles/
│   └── osint/                        ← profile ของ repo นี้
│       ├── SOUL.md, config.yaml      ← จาก repo
│       ├── skills/intelligence/      ← จาก repo
│       ├── .no-bundled-skills        ← จาก repo: ไม่เพิ่ม skill มาตรฐานของ Hermes
│       ├── .env                      ← ของคุณ: OPENROUTER_API_KEY, API_SERVER_KEY
│       ├── sessions/, memories/      ← บทสนทนาและความจำของเอเจนต์ osint
│       └── logs/                     ← log ของ profile (agent.log, errors.log)
└── workspace/                        ← workspace กลาง (terminal.cwd ของ osint)
    ├── collection20-10-2026_09-00/   ← แฟ้มงานของโหมดนักวิเคราะห์
    │   └── step1.md … step4.md
    └── report_20-10-2026_09-45.md    ← รายงานผู้บริหาร
```

## องค์ประกอบของ repo

repo นี้เป็น **Hermes profile distribution** คำสั่ง `hermes profile install` จะคัดลอกเฉพาะรายการที่กำหนดใน `distribution.yaml` เข้าไปใน profile

| ไฟล์ | หน้าที่ | ติดตั้งเข้า profile |
|---|---|---|
| `SOUL.md` | บุคลิกและกฎการทำงานของเอเจนต์ | ✓ |
| `skills/intelligence/` | skill `intelligence-analyzer` โหมดนักวิเคราะห์ข่าวกรองแบบ 4 ขั้นตอน (STEEPM) | ✓ |
| `config.yaml` | ค่าที่ต่างจากค่าเริ่มต้นของ Hermes ได้แก่ model, โฟลเดอร์ทำงาน, เครื่องมือ และ MCP server | ✓ |
| `.env.template` | ค่าลับที่ profile ต้องมี | ✓ (เป็น `.env.EXAMPLE`) |
| `.no-bundled-skills` | ให้ profile ใช้เฉพาะ skill ของ repo นี้ ไม่เพิ่ม skill มาตรฐานของ Hermes | ✓ |
| `distribution.yaml` | ชื่อ เวอร์ชัน เวอร์ชันของ Hermes ที่ต้องใช้ และรายการไฟล์ที่ติดตั้ง | ✓ |
| `docker-compose.yml`, `.env.example` | ชุดติดตั้ง Hermes บน Docker สำหรับผู้ที่ยังไม่มี Hermes | |
| `README.md`, `LICENSE` | เอกสาร | |

ชื่อ profile ใน Hermes เป็นตัวพิมพ์เล็กเสมอ จึงใช้ชื่อ `osint`

## หลักการทำงาน

```
แอปที่เรียกเอเจนต์ ──POST /p/osint/v1/responses──▶ hermes (gateway)
                                                  ① เลือก profile osint จาก path /p/osint
                                                  ② ตรวจ API_SERVER_KEY ของ profile osint
                                                  ③ ใส่ SOUL.md และรายการ skill ของ osint ลงใน prompt
                                                  ④ LLM (ผ่าน OpenRouter) คิดและเลือกเครื่องมือ วนจนได้คำตอบ
                                                     ├─ เครื่องมือของ Hermes: web_search, write_file, terminal …
                                                     └─ MCP: mcp-perplexity, mcp-thai-proofread, mcp-lightrag
                                                ◀── ส่งคำตอบกลับ (หรือส่งทีละส่วนแบบ stream)
```

ทุกครั้งที่เอเจนต์เรียกเครื่องมือ Hermes จะส่ง prompt ทั้งก้อนให้ LLM อีกรอบ คำสั่งที่เรียกเครื่องมือหลายครั้งจึงใช้ token และเวลามากขึ้นตามจำนวนรอบ (ดู[การวัดเวลาและค่าใช้จ่ายของแต่ละขั้น](#การวัดเวลาและค่าใช้จ่ายของแต่ละขั้น))

## เริ่มต้นใช้งาน

### สิ่งที่ต้องเตรียม

- **Hermes Agent เวอร์ชัน 0.21.6 ขึ้นไป** ถ้ายังไม่มี ใช้ `docker-compose.yml` ใน repo นี้ได้
- **OpenRouter API key** ขอได้ที่ https://openrouter.ai/keys
- **MCP server ทั้ง 3 ตัว** ที่ทำงานอยู่ใน docker network เดียวกับ Hermes หากยังไม่มี ให้ติดตั้งตาม README ของแต่ละตัว
  - [mcp-perplexity](https://github.com/chacharin/mcp-perplexity) ค้นหาเว็บและถามตอบผ่าน Perplexity
  - [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) ตรวจและแก้คำสะกดภาษาไทย (เข้าถึง workspace ผ่าน dashboard ของ Hermes หรือ mount `data/workspace`)
  - [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) คลังความรู้ LightRAG

  เอเจนต์ยังทำงานได้แม้ขาด MCP server บางตัว เพียงแต่จะไม่มีเครื่องมือของตัวนั้น

### 1. ติดตั้ง Hermes บน Docker (ข้ามได้ถ้ามี Hermes อยู่แล้ว)

```bash
git clone https://github.com/chacharin/harness-server.git
cd harness-server
docker network create agent_network   # สร้างครั้งแรกครั้งเดียว หากต้องการใช้ชื่ออื่นให้กำหนดใน DOCKER_NETWORK
docker compose up -d                  # ครั้งแรก Hermes จะสร้างโฟลเดอร์ data/ เอง
```

ค่าของ docker compose เช่น พอร์ตของ dashboard ปรับได้ด้วยการคัดลอก [`.env.example`](.env.example) เป็น `.env` แล้วสั่ง `docker compose up -d` อีกครั้ง

### 2. ติดตั้ง profile osint

```bash
docker exec -u hermes hermes hermes profile install github.com/chacharin/harness-server -y
```

(ถ้าติดตั้ง Hermes แบบปกติ ไม่ใช่ Docker ให้สั่ง `hermes profile install github.com/chacharin/harness-server`)

### 3. ใส่ค่าลับของ profile

```bash
cp data/profiles/osint/.env.EXAMPLE data/profiles/osint/.env   # แล้วแก้ OPENROUTER_API_KEY และ API_SERVER_KEY
```

ดูคำอธิบายแต่ละค่าใน [`.env.template`](.env.template) gateway จะค้นพบ profile ใหม่เองภายในไม่เกิน 30 วินาที

### 4. ตรวจสถานะ

```bash
docker exec hermes hermes profile list
docker exec hermes curl -s http://127.0.0.1:8642/p/osint/v1/models -H "Authorization: Bearer <API_SERVER_KEY ของ osint>"
```

หากได้รายการ model ที่มี `"id": "osint"` แปลว่าพร้อมใช้งาน และ `data/profiles/osint/logs/agent.log` ควรมีข้อความ `MCP: registered … into this profile scope`

### 5. ตั้งรหัสผ่าน dashboard

dashboard ที่เปิดให้เครื่องอื่นเข้าถึงได้ (`DASHBOARD_PUBLISH_ADDR=0.0.0.0`) จะไม่เริ่มทำงานจนกว่าจะตั้งรหัสผ่าน ให้สร้าง hash ของรหัสผ่านด้วยคำสั่ง

```bash
docker exec -w /opt/hermes hermes /opt/hermes/.venv/bin/python -c \
  "from plugins.dashboard_auth.basic import hash_password; print(hash_password('<รหัสผ่าน>'))"
```

แล้วเพิ่มในหัวข้อ `dashboard` ของ `data/config.yaml` (config ของ profile default ซึ่งเป็นเจ้าของ dashboard) จากนั้นสั่ง `docker compose restart dashboard`

```yaml
dashboard:
  basic_auth:
    username: admin
    password_hash: scrypt$16384$8$1$…   # ค่าที่ได้จากคำสั่งข้างต้น
```

หากกำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1` จะเปิดได้เฉพาะเครื่องนี้ และไม่ต้องตั้งรหัสผ่าน

## การเรียกใช้

เรียกใช้เอเจนต์ osint ได้ 3 ทาง

| ทาง | เหมาะกับ | วิธี |
|---|---|---|
| **API** | แอปของคุณ เช่น หน้าจอสั่งงาน | `http://hermes:8642/p/osint/v1` ส่ง `Authorization: Bearer <API_SERVER_KEY ของ osint>` |
| **dashboard** | ผู้ดูแลระบบ ดูบทสนทนา ตั้งค่า และแชททดสอบ | `http://<เครื่อง>:9119` |
| **terminal** | ทดสอบเร็ว ๆ บนเครื่องที่รัน Hermes | `docker exec -it -u hermes hermes hermes -p osint chat` |

ตัวอย่างการเรียกผ่าน API ด้วยไลบรารีของ OpenAI:

```python
from openai import OpenAI
client = OpenAI(base_url="http://hermes:8642/p/osint/v1", api_key="<API_SERVER_KEY ของ osint>")
reply = client.responses.create(model="osint", input="สรุปข่าวเด่นวันนี้")
print(reply.output_text)
```

ตัวอย่างการสั่งครั้งเดียวผ่าน terminal (ไม่เปิดหน้าแชท):

```bash
docker exec -u hermes hermes hermes -p osint chat -q "ค้นหาข่าวล่าสุดเกี่ยวกับนโยบาย AI ของไทย"
```

พอร์ต 8642 ไม่ได้เปิดออกนอก docker network แอปที่อยู่เครื่องอื่นต้องเชื่อมผ่าน HTTPS (reverse proxy) หรือเครือข่ายส่วนตัว แอปที่ตั้งค่าที่อยู่ของเอเจนต์และชื่อ profile แยกกัน ให้ใช้ที่อยู่ `http://hermes:8642/p/osint` และชื่อ profile (model) `osint`

## วิธีใช้งาน

ผู้ใช้สั่งเอเจนต์ด้วยภาษาปกติ เอเจนต์จะทำตามกฎใน SOUL และเลือกเครื่องมือให้เอง

### 1. โหมดนักวิเคราะห์ข่าวกรอง

ตัวอย่างคำสั่ง:

> ทำหน้าที่เป็นนักวิเคราะห์ หัวข้อ: สถานการณ์ความมั่นคงในทะเลอันดามัน
> act as an intelligence analyst. Topic: …

เอเจนต์จะโหลด skill `intelligence-analyzer` (กฎข้อ 1) แล้วทำงานทีละขั้น

| ขั้น | งาน | ไฟล์ที่ได้ใน workspace |
|---|---|---|
| 1 | สำรวจและรวบรวมข้อมูลเชิงยุทธศาสตร์ | สร้างแฟ้มงาน `collection<วันที่>_<เวลา>/` และ `step1.md` |
| 2 | ประเมินความน่าเชื่อถือของแหล่งข้อมูล | `step2.md` |
| 3 | วิเคราะห์ด้วยกรอบ STEEPM (สังคม เทคโนโลยี เศรษฐกิจ สิ่งแวดล้อม การเมือง การทหาร) ผ่านมุมมองสงครามลูกผสม | `step3.md` |
| 4 | เขียนรายงานสำหรับผู้บริหาร | `step4.md` และ `report_<วันที่>_<เวลา>.md` |

- ทุกขั้นปิดรายงานด้วย "กระผมรอให้ท่านสั่ง ให้ดำเนินการขั้นต่อไป (next)" แล้วรอ พิมพ์ **"ต่อไป"** หรือ **"next"** เพื่อไปขั้นถัดไป
- ระหว่างรอ สั่งแก้ผลของขั้นปัจจุบันได้ เอเจนต์จะเขียนทับ `stepN.md` รายงานใหม่ และรอคำสั่งอีกครั้ง
- ขั้นที่ 4 ปิดด้วย "จบภารกิจ" แล้วเอเจนต์จะกลับมาตอบแบบแชทปกติ
- ทุกขั้นตรวจคำสะกดภาษาไทยของไฟล์ที่เขียนด้วย `proofread_thai`
- สั่งเป็นภาษาอังกฤษ เอเจนต์จะทำงานและรายงานเป็นภาษาอังกฤษทั้งหมด (ปิดด้วย `Standing by…` และ `MISSION COMPLETE`)

### 2. ค้นหาข้อมูลบนเว็บ

> ค้นหาข่าวล่าสุดเกี่ยวกับนโยบาย AI ของไทย

เมื่อผู้ใช้สั่ง "ค้นหา" เอเจนต์จะใช้ `web_search` ของ Hermes ทันที (กฎข้อ 2) หากต้องการคำตอบที่สรุปพร้อมแหล่งอ้างอิง หรือการค้นคว้าเชิงลึก ให้ระบุว่าใช้ Perplexity เช่น "ถาม Perplexity ว่า …" หรือ "ค้นคว้าเชิงลึกด้วย Perplexity เรื่อง …"

### 3. บันทึกผลงานเป็นไฟล์

> บันทึกสรุปนี้ไว้
> จัดเก็บรายงานนี้เป็นไฟล์ .md

เอเจนต์จะสร้างไฟล์ใน workspace กลาง (`data/workspace/`) โดยตั้งชื่อไฟล์ตามเนื้อหาและใส่วันเวลากำกับ (กฎข้อ 3) หากไม่ระบุชนิดไฟล์ จะบันทึกเป็น `.txt`

### 4. ใช้งานคลังความรู้

> ค้นจากคลังความรู้ว่าเคยมีรายงานเรื่อง … หรือไม่
> เก็บรายงานนี้เข้าคลังความรู้ โดยตั้งชื่อว่า …
> ในคลังความรู้มีเอกสารอะไรบ้าง

เอเจนต์จะใช้เครื่องมือของ [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) ได้แก่ `lightrag_query`, `lightrag_insert` และ `lightrag_list_documents`

### 5. ตรวจคำสะกดภาษาไทย

> ตรวจคำสะกดภาษาไทยในไฟล์ report.md ให้หน่อย

เอเจนต์จะใช้เครื่องมือของ [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) แก้ไฟล์ใน workspace โดยสำรองไฟล์ต้นฉบับไว้ก่อนเสมอ

## เทคนิคการใช้

### สั่งโหมดนักวิเคราะห์ให้ได้ผลดี

- **ให้หัวข้อชัดเจนในคำสั่งแรก** ระบุประเด็น ขอบเขตเวลา และพื้นที่ เช่น "หัวข้อ: การซ้อมรบในทะเลจีนใต้ ช่วง 30 วันที่ผ่านมา" เอเจนต์จะใช้คำสั่งนี้เป็นกรอบของทั้ง 4 ขั้น
- **ตรวจผลก่อนพิมพ์ "ต่อไป" ทุกครั้ง** ขั้นถัดไปอ่านไฟล์ของขั้นก่อนหน้าเป็นข้อมูลนำเข้า การแก้ตั้งแต่ขั้นแรก ๆ จึงได้ผลดีกว่าแก้ที่รายงานขั้นสุดท้าย
- **ภารกิจละ 1 เซสชัน** เอเจนต์อ้างชื่อแฟ้มงานจากบทสนทนา ถ้าเริ่มภารกิจใหม่ในเซสชันเดิมขณะงานเก่ายังไม่จบ เอเจนต์จะถามยืนยันก่อน
- **เก็บรายงานเข้าคลังความรู้หลังจบภารกิจ** เช่น "เก็บรายงาน report_… เข้าคลังความรู้" เพื่อให้ภารกิจต่อไปค้นอ้างอิงได้

### การวัดเวลาและค่าใช้จ่ายของแต่ละขั้น

ทุกคำตอบของ API มี header `X-Hermes-Session-Id` ใช้ดึงข้อมูลของเซสชันได้ 2 ระดับ

| ข้อมูล | Route | ได้อะไร |
|---|---|---|
| ภาพรวมของเซสชัน | `GET /p/osint/api/sessions` | `input_tokens`, `output_tokens`, `tool_call_count`, `message_count`, `started_at`, `ended_at` |
| ทีละขั้น | `GET /p/osint/api/sessions/<id>/messages` | ทุกข้อความพร้อม `timestamp`, `role`, `tool_name` และ `finish_reason` |

เวลาของแต่ละขั้นคือผลต่างของ `timestamp` ระหว่างข้อความที่ต่อกัน ตัวอย่างจากคำสั่ง "สร้างไฟล์ทดสอบ" (ย่อ):

```json
{"data": [
  {"role": "user",      "timestamp": 1792458779.42, "content": "สร้างไฟล์ชื่อ osint-workspace-test.txt …"},
  {"role": "assistant", "timestamp": 1792458786.31, "finish_reason": "tool_calls"},
  {"role": "tool",      "timestamp": 1792458786.89, "tool_name": "write_file"},
  {"role": "assistant", "timestamp": 1792458788.90, "finish_reason": "stop", "content": "สร้างไฟล์เรียบร้อยแล้วครับ …"}
]}
```

| ขั้น | เวลา |
|---|---|
| LLM คิดและเลือกเครื่องมือ | 6.9 วินาที |
| `write_file` | 0.6 วินาที |
| LLM เขียนคำตอบ | 2.0 วินาที |

เวลาส่วนใหญ่อยู่ที่ LLM ไม่ใช่เครื่องมือ หากงานช้าผิดปกติ ให้ดูสถานะของผู้ให้บริการ LLM ก่อน

### ลดค่าใช้จ่ายต่อคำสั่ง

token ส่วนใหญ่ของทุกรอบคือคำอธิบายเครื่องมือที่ส่งให้ LLM ตัวเลขด้านล่างวัดจากคำถามสั้นหนึ่งประโยคในเซสชันใหม่

| สภาพ | input token ต่อรอบ |
|---|---|
| เครื่องมือครบ และ skill มาตรฐานของ Hermes ครบ (profile default) | 14,637 |
| เครื่องมือครบ และมีเฉพาะ skill ของ repo นี้ (profile osint) | 13,288 |
| ปิดเครื่องมือทั้งหมด | 806 |

ปิดเครื่องมือที่ไม่ใช้ได้ด้วย `agent.disabled_toolsets` ใน `config.yaml` ของ profile เช่น `[browser, code_execution, delegation]` ค่านี้มีผลกับทุกช่องทาง รวมถึง API และใส่ชื่อ MCP server ได้ด้วย (ส่วน `platform_toolsets.cli` มีผลเฉพาะ CLI)
การเปลี่ยนแปลงมีผลกับเซสชันใหม่เท่านั้น เพราะ Hermes เก็บ prompt และรายการเครื่องมือของแต่ละเซสชันไว้คงเดิม

### เลือกเครื่องมือค้นหาให้เหมาะกับงาน

| ต้องการ | สั่งว่า | เครื่องมือ |
|---|---|---|
| ลิงก์และข่าวล่าสุดแบบเร็ว | "ค้นหา …" | `web_search` ของ Hermes |
| คำตอบสรุปพร้อมแหล่งอ้างอิง | "ถาม Perplexity ว่า …" | `perplexity_ask` |
| ค้นคว้าเชิงลึกหลายแหล่ง (หลายนาที ราคาสูง) | "ค้นคว้าเชิงลึกด้วย Perplexity เรื่อง …" | `perplexity_research` |
| เอกสารที่เคยเก็บไว้ | "ค้นจากคลังความรู้ว่า …" | `lightrag_query` |

## รูปแบบ JSON ของคำขอและผลลัพธ์

API ของเอเจนต์เป็นแบบ OpenAI-compatible ทุก route ของ profile osint ขึ้นต้นด้วย `/p/osint`

| Route | ใช้ทำอะไร | ต้องใช้ key |
|---|---|---|
| `POST /p/osint/v1/responses` | สั่งงานเอเจนต์และรับคำตอบ (Responses API) | ✓ |
| `GET /p/osint/v1/responses/<id>` | อ่านคำตอบเดิมอีกครั้ง | ✓ |
| `GET /p/osint/v1/models` | ดูรายชื่อ model ที่เรียกได้ | ✓ |
| `GET /p/osint/v1/toolsets` | ดูชุดเครื่องมือที่เอเจนต์ได้รับ พร้อมสถานะเปิด/ปิด | ✓ |
| `GET /p/osint/api/sessions` และ `…/<id>/messages` | ภาพรวมและขั้นตอนของแต่ละเซสชัน | ✓ |
| `GET /health` | ตรวจว่า gateway ทำงานอยู่ | |

ทุกคำขอที่ต้องใช้ key ต้องส่ง header `Authorization: Bearer <API_SERVER_KEY ของ osint>` key ของ profile default ใช้กับ `/p/osint` ไม่ได้

### สั่งงานเอเจนต์ (`POST /p/osint/v1/responses`)

คำขอ:

```json
{"model": "osint", "input": "บอกวันและเวลาปัจจุบันของประเทศไทย โดยใช้คำสั่ง date ใน terminal แล้วตอบสั้น ๆ", "stream": false}
```

| ค่า | ความหมาย |
|---|---|
| `model` | ชื่อ profile (`osint`) ส่วน model ของ LLM กำหนดใน `config.yaml` ของ profile |
| `input` | คำสั่งหรือคำถาม |
| `stream` | `true` = ส่งผลลัพธ์ทีละส่วนแบบ Server-Sent Events ระหว่างที่เอเจนต์ทำงาน เหมาะกับงานที่ใช้เวลานาน |
| `previous_response_id` | (ไม่บังคับ) `id` ของคำตอบก่อนหน้า เพื่อคุยต่อในบทสนทนาเดิม เช่น ส่ง "ต่อไป" ในโหมดนักวิเคราะห์ |

ผลลัพธ์ (ย่อ):

```json
{
  "object": "response",
  "status": "completed",
  "model": "osint",
  "output": [
    {"type": "reasoning", "status": "completed"},
    {"type": "function_call", "name": "terminal", "call_id": "call-f191…",
     "arguments": "{\"command\": \"TZ=\\\"Asia/Bangkok\\\" date\"}"},
    {"type": "function_call_output", "call_id": "call-f191…",
     "output": [{"type": "input_text", "text": "{\"output\": \"Tue Oct 20 08:12:38 +07 2026\", \"exit_code\": 0, \"error\": null}"}]},
    {"type": "reasoning", "status": "completed"},
    {"type": "message", "role": "assistant",
     "content": [{"type": "output_text", "text": "วันอังคารที่ 20 ตุลาคม 2026 เวลา 08:12 น. ครับ"}]}
  ],
  "usage": {"input_tokens": 26778, "output_tokens": 220, "total_tokens": 26998}
}
```

คำตอบของเอเจนต์อยู่ใน `output` รายการที่มี `"type": "message"` ส่วน `usage.input_tokens` นับรวมทุกรอบ ตัวอย่างนี้เรียกเครื่องมือ 1 ครั้ง จึงส่ง prompt 2 รอบ ใช้เวลารวมประมาณ 9 วินาที

### ข้อผิดพลาด

| กรณี | ผลลัพธ์ |
|---|---|
| ไม่ส่ง key, key ผิด หรือใช้ key ของ profile อื่น | HTTP 401 `{"error": {"message": "Invalid gateway API key (API_SERVER_KEY)", "type": "gateway_auth_error", "code": "gateway_auth_failed"}}` |
| OpenRouter API key ผิดหรือวงเงินหมด | คำตอบแจ้งข้อผิดพลาดจาก OpenRouter ให้ตรวจ `OPENROUTER_API_KEY` ใน `.env` ของ profile และวงเงินที่ https://openrouter.ai/settings/credits |
| MCP server ตัวใดไม่ทำงาน | เอเจนต์ยังทำงานได้ แต่ไม่มีเครื่องมือของตัวนั้น ตรวจได้จาก log `MCP: registered` |

### ตรวจสถานะ (`GET /health`)

```json
{"status": "ok", "platform": "hermes-agent", "version": "0.21.6"}
```

### ทดลองด้วย curl

พอร์ต 8642 อยู่ภายใน docker network จึงต้องเรียกจาก container ที่อยู่ใน network เดียวกัน เช่น

```bash
docker run --rm --network agent_network curlimages/curl -s http://hermes:8642/p/osint/v1/responses \
  -H "Authorization: Bearer <API_SERVER_KEY ของ osint>" -H "Content-Type: application/json" \
  -d '{"model": "osint", "input": "สวัสดี", "stream": false}'
```

บน Windows คำสั่ง curl อาจส่งภาษาไทยที่พิมพ์ในบรรทัดคำสั่งผิดเพี้ยนเป็น `?` ให้บันทึก JSON ของคำขอเป็นไฟล์ UTF-8 แล้วส่งด้วย `-d @request.json` แทน

## การปรับแต่งและการอัปเดต

ค่าต่อไปนี้อยู่ในโฟลเดอร์ของ profile (`data/profiles/osint/`) แก้ได้โดยตรงหรือผ่าน dashboard เมื่อแก้ไขแล้วมีผลกับเซสชันใหม่

- **`SOUL.md`** บุคลิกและกฎการทำงาน เขียนเป็นภาษาปกติได้เลย เช่น เพิ่มกฎว่าเมื่อผู้ใช้สั่งคำใดให้ใช้เครื่องมือใด
- **`skills/`** เพิ่ม skill ของตัวเองเป็นโฟลเดอร์ที่มีไฟล์ `SKILL.md` (ดูตัวอย่างจาก `intelligence-analyzer`)
- **`model` ใน `config.yaml`** เปลี่ยน LLM ของเอเจนต์ ควรเลือก model ที่รองรับภาษาไทยและการเรียกใช้เครื่องมือได้ดี
- **`agent.max_turns` ใน `config.yaml`** จำนวนรอบเรียกเครื่องมือสูงสุดต่อหนึ่งคำสั่ง เพิ่มได้หากงานวิเคราะห์ยาวถูกตัดกลางคัน
- **`agent.disabled_toolsets` ใน `config.yaml`** ปิดเครื่องมือหรือ MCP server ที่ไม่ใช้ (ดู[ลดค่าใช้จ่ายต่อคำสั่ง](#ลดค่าใช้จ่ายต่อคำสั่ง))
- **`mcp_servers` ใน `config.yaml`** เพิ่มหรือถอด MCP server

| ต้องการ | คำสั่ง |
|---|---|
| อัปเดตเอเจนต์เป็นเวอร์ชันใหม่ของ repo นี้ | `docker exec -u hermes hermes hermes profile update osint` |
| เพิ่ม skill มาตรฐานของ Hermes ให้ profile osint | `docker exec -u hermes hermes hermes -p osint skills opt-in --sync` |
| อัปเดต Hermes | กำหนด `HERMES_IMAGE` ใน `.env` แล้วสั่ง `docker compose pull` และ `docker compose up -d` |

`hermes profile update` แทนที่ `SOUL.md` และ `skills/` ด้วยเวอร์ชันใหม่ ส่วน `config.yaml`, `.env`, บทสนทนา และความจำของเอเจนต์คงไว้ตามเดิม
skill `hermes-agent` เป็น skill ที่ Hermes เพิ่มให้ทุก profile เสมอ แม้จะมี `.no-bundled-skills`

## แก้ปัญหาที่พบบ่อย

| อาการ | สาเหตุและวิธีแก้ |
|---|---|
| เรียก `/p/osint/v1/...` ได้ HTTP 401 | ใช้ key ผิด profile ให้ใช้ `API_SERVER_KEY` จาก `data/profiles/osint/.env` ไม่ใช่ของ `data/.env` |
| เรียก `/p/osint/...` แล้วไม่พบ profile | gateway ยังไม่ค้นพบ profile รอ 30 วินาทีหลังติดตั้ง หรือสั่ง `docker compose restart gateway` |
| log มีข้อความ `config predates version 12` | `config.yaml` ของ profile ไม่มี `_config_version` ให้เพิ่มค่าเดียวกับใน `data/config.yaml` |
| เอเจนต์บอกว่าไม่มีเครื่องมือ perplexity หรือ lightrag | MCP server ตัวนั้นไม่ทำงาน หรือไม่อยู่ใน docker network เดียวกัน ตรวจ `MCP: registered` ใน log ของ profile |
| `proofread_thai` หาไฟล์ไม่เจอ | ไม่ได้ตั้ง `PATH_PREFIXES=/opt/data/workspace/` หรือ mcp-thai-proofread เข้าถึง workspace ไม่ได้ (ดู `workspace` ใน `/health` ของ mcp-thai-proofread: ยังไม่ได้ตั้งบัญชี dashboard หรือยังไม่ได้ mount `data/workspace`) |
| dashboard ไม่เปิด | ยังไม่ได้ตั้ง `dashboard.basic_auth` ใน `data/config.yaml` (ดูขั้นตอนที่ 5) |
| ตอบช้าหรือค้าง | ดูสถานะผู้ให้บริการ LLM และวงเงิน OpenRouter ก่อน เพราะเวลาส่วนใหญ่อยู่ที่ LLM |

## ความปลอดภัย

- **API ของเอเจนต์** (พอร์ต 8642) เปิดเฉพาะภายใน docker network และต้องใช้ `API_SERVER_KEY` ของแต่ละ profile ทุกครั้ง
  ผู้ที่มี key นี้สั่งเอเจนต์ใช้ทุกเครื่องมือได้ รวมถึง `terminal` ที่รันคำสั่งใน container ของ Hermes โดยตรง จึงต้องเก็บ key เป็นความลับ และให้เฉพาะแอปที่ไว้ใจได้
- **dashboard** (พอร์ต 9119) เปิดให้เครื่องอื่นในเครือข่ายเข้าถึงได้เป็นค่าเริ่มต้น (`DASHBOARD_PUBLISH_ADDR=0.0.0.0`) และต้องเข้าสู่ระบบด้วยรหัสผ่านที่ตั้งไว้ทุกครั้ง หากไม่จำเป็น ให้กำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1`
- **ค่าลับทั้งหมด** อยู่ใน `.env` ของแต่ละ profile, `data/auth.json` และรหัสผ่าน dashboard ใน `data/config.yaml` ซึ่ง `.gitignore` กันไม่ให้ขึ้น git ทั้งโฟลเดอร์ `data/`
- ควรตั้งวงเงินของ OpenRouter API key ไว้ เพื่อจำกัดค่าใช้จ่ายหากเอเจนต์ทำงานวนนานผิดปกติ

## สำหรับนักพัฒนา

### ทดลองติดตั้งจากเครื่องก่อน push

`hermes profile install` รับโฟลเดอร์ที่มี `distribution.yaml` ได้ด้วย ส่งออกเฉพาะไฟล์ที่ git ติดตามไปไว้ใน `data/` แล้วติดตั้งจากที่นั่น

```bash
git checkout-index -a --prefix=data/.dist-osint/
docker exec -u hermes hermes hermes profile install /opt/data/.dist-osint --force -y
```

`--force` แทนที่ `SOUL.md`, `skills/` และ `config.yaml` ด้วยของ repo ส่วน `.env`, บทสนทนา และความจำคงไว้ เสร็จแล้วลบ `data/.dist-osint/` ได้

### ออกเวอร์ชันใหม่

แก้ `version` ใน `distribution.yaml` แล้ว push ผู้ใช้สั่ง `hermes profile update osint` เพื่อรับเวอร์ชันใหม่ (Hermes จำที่มาของ profile ไว้ตอนติดตั้ง)

### เมื่ออัปเดต Hermes

ตรวจว่า `/health` แสดงเวอร์ชันใหม่ log ของ profile osint แสดง `MCP: registered` และโหมดนักวิเคราะห์ยังทำงานได้ ก่อนแก้ `hermes_requires` ใน `distribution.yaml` และค่าเริ่มต้นใน `docker-compose.yml`
ถ้า Hermes เวอร์ชันใหม่เปลี่ยนรูปแบบ config ให้ปรับ `_config_version` ใน `config.yaml` ตามค่าใน `data/config.yaml` ที่ Hermes สร้างใหม่

## สัญญาอนุญาต

[MIT](LICENSE) © 2026 Chacharin Lertyosbordin
Hermes Agent เป็นลิขสิทธิ์ของ Nous Research ภายใต้สัญญาอนุญาต MIT ([ซอร์สโค้ด](https://github.com/NousResearch/hermes-agent))
