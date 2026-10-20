# OSINT-Harness-Profile

เอเจนต์ AI สำหรับงานข่าวกรองจากแหล่งข้อมูลเปิด (OSINT) ที่สร้างบน [Hermes Agent](https://github.com/NousResearch/hermes-agent) พร้อมบุคลิก กฎการทำงาน และ skill นักวิเคราะห์ข่าวกรอง
ติดตั้งเป็น **profile ของ Hermes ชื่อ `osint`** ด้วยคำสั่งเดียว และให้บริการ API แบบ OpenAI-compatible แก่แอปอื่น โดยเชื่อมต่อเครื่องมือผ่าน MCP ได้แก่ Perplexity, ตรวจคำสะกดภาษาไทย และคลังความรู้ LightRAG

ผู้พัฒนา: **Chacharin Lertyosbordin**

> โปรเจกต์นี้คือการตั้งค่าและเนื้อหาของเอเจนต์ (SOUL และ skill) ที่ใช้กับ Hermes Agent ไม่ได้รวมตัว Hermes มาด้วย
> Hermes Agent พัฒนาโดย Nous Research ภายใต้สัญญาอนุญาต MIT และโปรเจกต์นี้ไม่ใช่ผลงานทางการของ Nous Research

## ภาพรวม

เอเจนต์ osint ทำงานได้ 2 แบบ

- **ผู้ช่วยทั่วไป** ตอบคำถามเป็นภาษาไทยและอังกฤษ ค้นเว็บ ถามตอบผ่าน Perplexity ใช้คลังความรู้ ตรวจคำสะกดภาษาไทย และบันทึกผลงานเป็นไฟล์
- **นักวิเคราะห์ข่าวกรอง** เมื่อสั่ง "ทำหน้าที่เป็นนักวิเคราะห์" เอเจนต์จะทำงาน 4 ขั้น (รวบรวมข้อมูล → ประเมินแหล่งข้อมูล → วิเคราะห์ STEEPM → รายงานผู้บริหาร) ทีละขั้น เขียนผลแต่ละขั้นเป็นไฟล์ และรอคำสั่งก่อนขึ้นขั้นถัดไป

## สถาปัตยกรรม

### 3 ชั้นที่ประกอบกันเป็นระบบ

| ชั้น | มาจาก | ให้อะไร |
|---|---|---|
| **image ของ Hermes** | `nousresearch/hermes-agent:v0.21.6` (Docker Hub) | ตัวเอเจนต์ทั้งหมด: gateway และ API, dashboard, เครื่องมือในตัว (web_search, file, terminal, memory …), ระบบ skill, การเชื่อม MCP และระบบ profile |
| **profile osint** | repo นี้ ติดตั้งด้วย `hermes profile install` | ตัวตนของเอเจนต์: `SOUL.md`, skill `intelligence-analyzer` และ `config.yaml` (model, โฟลเดอร์ทำงาน, MCP) |
| **การติดตั้งของคุณ** | โฟลเดอร์ `data/` และ container อื่นใน docker network | ค่าลับ (`.env`), บทสนทนา, ความจำ, workspace และ MCP server ทั้ง 3 ตัว |

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
│       ├── plugins/usage-telemetry/  ← จาก repo: บันทึกข้อมูลการใช้งาน
│       ├── .env                      ← ของคุณ: OPENROUTER_API_KEY, API_SERVER_KEY
│       ├── sessions/, memories/      ← บทสนทนาและความจำของเอเจนต์ osint
│       └── logs/                     ← log ของ profile (agent.log, errors.log)
│           └── usage/                ← ข้อมูลการใช้งาน usage-<วันที่>.jsonl (plugin usage-telemetry)
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
| `config.yaml` | ค่าที่ต่างจากค่าเริ่มต้นของ Hermes ได้แก่ model, โฟลเดอร์ทำงาน, เครื่องมือ, plugin และ MCP server | ✓ |
| `.env.template` | ค่าลับที่ profile ต้องมี | ✓ (เป็น `.env.EXAMPLE`) |
| `.no-bundled-skills` | ให้ profile ใช้เฉพาะ skill ของ repo นี้ ไม่เพิ่ม skill มาตรฐานของ Hermes | ✓ |
| `plugins/usage-telemetry/` | plugin บันทึก token เวลา และค่าใช้จ่ายของการเรียก LLM และเครื่องมือทุกครั้ง (ดู[ข้อมูลการใช้งานสำหรับงานวิจัย](#ข้อมูลการใช้งานสำหรับงานวิจัย)) | ✓ |
| `distribution.yaml` | ชื่อ เวอร์ชัน เวอร์ชันของ Hermes ที่ต้องใช้ และรายการไฟล์ที่ติดตั้ง | ✓ |
| `docker-compose.yml`, `.env.example` | ชุดติดตั้ง Hermes บน Docker สำหรับผู้ที่ยังไม่มี Hermes | |
| `README.md`, `LICENSE` | เอกสาร | |

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
git clone https://github.com/chacharin/osint-harness-profile.git
cd osint-harness-profile
docker network create agent_network   # สร้างครั้งแรกครั้งเดียว หากต้องการใช้ชื่ออื่นให้กำหนดใน DOCKER_NETWORK
docker compose up -d                  # ครั้งแรก Hermes จะสร้างโฟลเดอร์ data/ เอง
```

ค่าของ docker compose เช่น พอร์ตของ dashboard ปรับได้ด้วยการคัดลอก [`.env.example`](.env.example) เป็น `.env` แล้วสั่ง `docker compose up -d` อีกครั้ง

### 2. ติดตั้ง profile osint

```bash
docker exec -u hermes hermes hermes profile install github.com/chacharin/osint-harness-profile -y
```

(ถ้าติดตั้ง Hermes แบบปกติ ไม่ใช่ Docker ให้สั่ง `hermes profile install github.com/chacharin/osint-harness-profile`)

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

หากต้องการสร้างแอปของตัวเอง เช่น หน้าจอสั่งงานที่แสดงขั้นตอนการทำงาน เปิดไฟล์ผลงาน และเปิด/ปิด skill ได้ ดู[สร้างแอปที่สั่งงานเอเจนต์](#สร้างแอปที่สั่งงานเอเจนต์)

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
- ระหว่างรอ พิมพ์ **"ต่อไป"** สามารถสั่งแก้ผลของขั้นปัจจุบันได้ เอเจนต์จะเขียนทับ `stepN.md` รายงานใหม่ และรอคำสั่งอีกครั้ง
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

## ข้อมูลการใช้งานสำหรับงานวิจัย

ทุกกระบวนการเบื้องหลังหนึ่งคำสั่งบันทึก token เวลา และค่าใช้จ่ายของตัวเองในรูปแบบเดียวกัน (schema `harness-usage/1`)
จึงรวมเป็นชุดข้อมูลเดียวสำหรับวิจัยและปรับประสิทธิภาพของฮาร์ดแวร์และซอฟต์แวร์ได้ เช่น เทียบ model ผู้ให้บริการ เครื่องที่รัน หรือจำนวนเครื่องมือที่เปิดไว้
ทุกแหล่งบันทึกเฉพาะจำนวน ขนาด id และเวลา ไม่มีคำสั่ง คำตอบ หรือผลของเครื่องมือ

| กระบวนการ | ผู้บันทึก | อ่านได้ที่ |
|---|---|---|
| LLM หลักของเอเจนต์ (ทุกรอบ) LLM งานเสริม เช่น ตั้งชื่อเซสชัน และการเรียกเครื่องมือทุกตัว | plugin `usage-telemetry` ของ repo นี้ | `data/profiles/osint/logs/usage/usage-<วันที่>.jsonl` |
| LLM ที่ตรวจคำสะกด | [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) | `GET http://mcp-thai-proofread:8800/usage` |
| Perplexity (token ค่าค้นเว็บ และค่าใช้จ่าย) | [mcp-perplexity](https://github.com/chacharin/mcp-perplexity) | `GET http://mcp-perplexity:8081/usage` |
| LLM และ embedding ที่ LightRAG เรียกเอง | มิเตอร์ของ [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) (ต้องเปิด) | `GET http://mcp-lightrag:8700/usage` |

แอปที่สั่งงานเอเจนต์ (เช่น collector) รวมทุกแหล่งเข้ากับคำสั่งของตัวเองได้ ดู[ข้อ 8 ของสร้างแอปที่สั่งงานเอเจนต์](#8-รวบรวมข้อมูลการใช้งาน)

### plugin usage-telemetry

plugin นี้ใช้ hook ของ Hermes (`post_api_request`, `post_auxiliary_call`, `post_tool_call`, `on_session_end` …) บันทึกหนึ่งบรรทัดต่อหนึ่งเหตุการณ์

| kind | เกิดเมื่อ | ข้อมูลสำคัญ |
|---|---|---|
| `llm_call` | เรียก LLM หลักหนึ่งครั้ง | `input_tokens`, `cache_read_tokens`, `cache_write_tokens`, `output_tokens`, `reasoning_tokens`, `cost_usd`, `duration_s`, `ttfb_s`, `output_tps`, `upstream_provider` (ผู้ให้บริการที่รันจริง) และ `detail` (จำนวนข้อความ จำนวนเครื่องมือที่ส่งให้ LLM ขนาดคำขอ ค่าประมาณ token ของ Hermes) |
| `aux_call` | เรียก LLM งานเสริม | ข้อมูลเดียวกับ `llm_call` และชื่องานใน `tool` เช่น `title_generation` |
| `tool_call` | เรียกเครื่องมือหนึ่งครั้ง รวมเครื่องมือ MCP (`mcp__<server>__<tool>`) | `duration_s`, `status`, ขนาดของค่าที่ส่งและผลลัพธ์ |
| `api_error` | เรียก LLM ไม่สำเร็จ | ชนิดของข้อผิดพลาด HTTP status และจำนวนครั้งที่ลองใหม่ |
| `turn_end` | จบหนึ่งคำสั่ง | สำเร็จ ล้มเหลว หรือถูกขัดจังหวะ และเหตุผล |
| `process` | ครั้งแรกของแต่ละ process | เวอร์ชันของ Hermes, Python, ระบบปฏิบัติการ, จำนวน CPU และหน่วยความจำของเครื่อง |

ตัวอย่างหนึ่งบรรทัด (`llm_call` รอบที่สองของคำสั่งหนึ่ง ซึ่งอ่าน prompt เดิมจาก cache):

```json
{"schema": "harness-usage/1", "ts": 1792465715.387, "component": "hermes", "profile": "osint", "host": "413b59fe0213",
 "kind": "llm_call", "session_id": "bc8a5a06-…", "turn_id": "bc8a5a06-…:b57d9558", "request_id": "…:api:2",
 "model": "google/gemma-4-31b-it", "provider": "openrouter", "upstream_provider": "Google", "endpoint_host": "openrouter.ai",
 "started_at": 1792465713.361, "ended_at": 1792465715.359, "duration_s": 1.998, "ttfb_s": 1.372,
 "input_tokens": 189, "output_tokens": 59, "reasoning_tokens": 35, "cache_read_tokens": 13344, "cache_write_tokens": 0,
 "prompt_tokens": 13533, "total_tokens": 13592, "output_tps": 94.23, "cost_usd": 0.002725, "cost_status": "upper_bound",
 "status": "ok", "finish_reason": "stop",
 "detail": {"approx_input_tokens": 3143, "request_chars": 12572, "tool_count": 24, "message_count": 4, "api_call_count": 2}}
```

- `cost_usd` คือราคาที่ Hermes ประมาณจากรายการราคาของผู้ให้บริการ หากผู้ให้บริการไม่ประกาศราคาของ cache plugin จะคิด token ที่อ่านจาก cache ในราคา input ปกติ และระบุ `cost_status` เป็น `upper_bound` (ค่าจริงไม่เกินนี้)
- ค่าใช้จ่ายจริงที่ OpenRouter เรียกเก็บ ดูได้จากหน้า Activity ของ OpenRouter ซึ่งส่งออกเป็น CSV ได้ ใช้ตรวจทานกับข้อมูลชุดนี้
- เปิดใช้ด้วย `plugins.enabled: [usage-telemetry]` ใน `config.yaml` ของ profile ซึ่งการติดตั้งใหม่มีให้แล้ว profile ที่ติดตั้งก่อนเวอร์ชัน 0.4.0 ต้องเพิ่มบรรทัดนี้เอง เพราะ `hermes profile update` ไม่เขียนทับ `config.yaml` แล้วสั่ง `docker compose restart gateway`
- ย้ายไฟล์ไปที่อื่นได้ด้วยตัวแปร `HERMES_USAGE_DIR` ใน `.env` ของ profile

### สิ่งที่ข้อมูลชุดนี้แสดงให้เห็นแล้ว

ตัวเลขจากคำสั่งทดสอบหนึ่งคำสั่ง ที่ตรวจคำสะกดหนึ่งคำ ค้นคลังความรู้ และถาม Perplexity หนึ่งข้อ

| สิ่งที่พบ | ตัวเลข |
|---|---|
| prompt ของเอเจนต์ส่วนใหญ่คือคำอธิบายเครื่องมือ และถูกส่งใหม่ทุกรอบ | 3 รอบ รวม prompt 44,187 token แต่เป็น token ใหม่เพียง 17,403 ที่เหลือ 26,784 อ่านจาก cache |
| ค่าประมาณ token ของ Hermes เองต่ำกว่าจริงมากสำหรับภาษาไทยและคำอธิบายเครื่องมือ | `approx_input_tokens` 3,143 เทียบกับ prompt จริง 13,533 |
| token ที่มองไม่เห็นจากหน้าจอ | LightRAG เรียก LLM 2 ครั้งและ embedding 1 ครั้งต่อหนึ่งคำถาม (ราว 5,400 token) และ Perplexity ใช้ prompt 5,724 token กับค่าค้นเว็บ 0.001 USD ต่อหนึ่งคำถาม |
| เวลาส่วนใหญ่อยู่ที่ LLM | LLM ของเอเจนต์ 14.8 วินาที จากทั้งหมด 24.3 วินาที (TTFB เฉลี่ย 2.6 วินาที ความเร็วเฉลี่ย 94 token/วินาที) |

## สร้างแอปที่สั่งงานเอเจนต์

หัวข้อนี้สำหรับผู้ที่ต้องการสร้างแอปของตัวเองบนเอเจนต์ osint (หรือ profile อื่นของ Hermes) เช่น หน้าจอสั่งงาน ระบบอัตโนมัติ หรือบอต
ทุกอย่างใช้ HTTP อย่างเดียว แอปจึงเขียนด้วยภาษาใดก็ได้ และอยู่คนละเครื่องกับ Hermes ได้

### API 2 ชุดที่แอปใช้

| API | ที่อยู่ | ยืนยันตัวตน | ใช้ทำอะไร |
|---|---|---|---|
| **gateway** | `http://hermes:8642/p/osint` | header `Authorization: Bearer <API_SERVER_KEY ของ osint>` | สั่งงานเอเจนต์ รับผลแบบ stream อ่านขั้นตอนของเซสชัน และลบบทสนทนา |
| **dashboard** | `http://hermes-dashboard:9119` | เข้าสู่ระบบด้วยชื่อผู้ใช้และรหัสผ่าน dashboard แล้วใช้ cookie ที่ได้ | อ่านและเขียนไฟล์ใน workspace และเปลี่ยนการตั้งค่าของ profile (เปิด/ปิด skill และเครื่องมือ เปลี่ยน model) |

แอปที่แค่สั่งงานและแสดงผลใช้เฉพาะ gateway ส่วน dashboard จำเป็นเมื่อแอปต้องเปิดไฟล์ที่เอเจนต์เขียน หรือให้ผู้ใช้ปรับการตั้งค่าได้เอง
เก็บค่าทั้งหมดไว้ใน `.env` ของแอป เช่น

```bash
HERMES_BASE_URL=http://hermes:8642/p/osint    # ที่อยู่ gateway ของ profile (ลงท้ายด้วย /p/<profile>)
HERMES_PROFILE=osint                          # ใช้เป็นค่า model ในคำขอ
HERMES_KEY=<API_SERVER_KEY ของ osint>
HERMES_DASHBOARD_URL=http://hermes-dashboard:9119
HERMES_DASHBOARD_USER=<ชื่อผู้ใช้ dashboard>
HERMES_DASHBOARD_PASSWORD=<รหัสผ่าน dashboard>
```

เมื่อแอปอยู่คนละเครื่องกับ Hermes ให้เปลี่ยนที่อยู่ทั้งสองเป็นที่อยู่ที่เข้าถึงได้จากเครื่องนั้น และเชื่อมผ่าน HTTPS หรือ VPN

### 1. สั่งงานและคุยต่อในบทสนทนาเดิม

ส่ง `POST /v1/responses` ทุกครั้งที่ผู้ใช้สั่งงาน แล้วเก็บ `id` ของคำตอบ (ขึ้นต้นด้วย `resp_`) ไว้กับบทสนทนานั้น
คำสั่งถัดไปในบทสนทนาเดียวกันให้ส่ง `previous_response_id` เป็น `id` ล่าสุด เอเจนต์จะจำทุกอย่างก่อนหน้าได้ ส่วนบทสนทนาใหม่ไม่ต้องส่งค่านี้

```
บทสนทนา A:  "ทำหน้าที่เป็นนักวิเคราะห์ หัวข้อ …"            → resp_1
            "ต่อไป"  + previous_response_id = resp_1   → resp_2
            "ต่อไป"  + previous_response_id = resp_2   → resp_3
```

แอปจึงต้องเก็บแค่ `id` ล่าสุดของแต่ละบทสนทนา Hermes เก็บเนื้อหาทั้งหมดไว้เอง

### 2. รับผลแบบ stream

งานของเอเจนต์มักใช้เวลาหลายนาที ควรส่ง `"stream": true` แล้วอ่านผลทีละ event แบบ Server-Sent Events (บรรทัด `data: <JSON>`)
ลำดับ event จริงของคำสั่งที่เรียกเครื่องมือ 1 ครั้ง:

| event (`type`) | ใช้ทำอะไรในแอป |
|---|---|
| `response.created` | เก็บ `response.id` ไว้เป็น `previous_response_id` ของคำสั่งถัดไป |
| `response.output_item.added` / `.done` ที่ `item.type` = `reasoning` | ช่วงที่ LLM คิด (ข้อความคิดมาใน `response.reasoning_summary_text.delta`) |
| `response.output_item.added` ที่ `item.type` = `function_call` | เอเจนต์เริ่มเรียกเครื่องมือ: `item.name` คือชื่อเครื่องมือ `item.arguments` คือค่าที่ส่ง |
| `response.output_item.added` ที่ `item.type` = `function_call_output` | ผลจากเครื่องมือ (`item.output`) |
| `response.output_text.delta` | ข้อความคำตอบทีละส่วน (`delta`) ต่อกันแสดงผลได้ทันที |
| `response.completed` | จบงาน: `response.usage` มี `input_tokens`, `output_tokens`, `total_tokens` |
| `response.failed` / `response.incomplete` | งานล้มเหลวหรือถูกตัด: ดู `response.error` |

ข้อควรรู้
- header `X-Hermes-Session-Id` ของคำตอบคือ id ของเซสชัน ใช้อ่านขั้นตอนอย่างละเอียดภายหลัง (ข้อ 3)
- **Hermes ไม่ปิดการเชื่อมต่อเองหลัง event สุดท้าย** แอปต้องปิดเองเมื่อได้ `response.completed`, `response.failed` หรือ `response.incomplete` มิฉะนั้นจะรอจนหมดเวลา
- ตั้ง read timeout ให้ยาว (เช่น 15 นาที) เพราะช่วงที่เครื่องมือทำงานนาน เช่น `perplexity_research` อาจไม่มี event เลยหลายนาที
- `response.completed` ไม่ได้รับประกันว่ามีคำตอบ หากการเรียก LLM ครั้งสุดท้ายล้มเหลว (เช่น HTTP 429) งานจะจบโดยไม่มี `output_text` ให้ถือว่างานยังไม่เสร็จ และแจ้งผู้ใช้

ตัวอย่างการสร้างไคลเอนต์อย่างง่ายด้วย Python (`httpx`):

```python
import json, os, httpx

BASE, KEY, PROFILE = os.environ["HERMES_BASE_URL"], os.environ["HERMES_KEY"], os.environ["HERMES_PROFILE"]
END = {"response.completed", "response.failed", "response.incomplete"}

def ask(text: str, previous_id: str | None = None) -> str | None:
    body = {"model": PROFILE, "input": text, "stream": True}
    if previous_id:
        body["previous_response_id"] = previous_id
    headers = {"Authorization": f"Bearer {KEY}", "Accept": "text/event-stream"}
    timeout = httpx.Timeout(15, read=900)
    with httpx.stream("POST", f"{BASE}/v1/responses", json=body, headers=headers, timeout=timeout) as r:
        r.raise_for_status()
        print("session:", r.headers.get("X-Hermes-Session-Id"))
        response_id = None
        for line in r.iter_lines():
            if not line.startswith("data:"):
                continue
            ev = json.loads(line[5:])
            kind, item = ev.get("type"), ev.get("item") or {}
            if kind == "response.created":
                response_id = ev["response"]["id"]
            elif kind == "response.output_item.added" and item.get("type") == "function_call":
                print(f"\n[เครื่องมือ] {item['name']} {item.get('arguments', '')[:80]}")
            elif kind == "response.output_text.delta":
                print(ev["delta"], end="", flush=True)
            elif kind in END:
                print("\n", kind, ev["response"].get("usage"))
                break                      # ปิดการเชื่อมต่อเอง
    return response_id

rid = ask("ทำหน้าที่เป็นนักวิเคราะห์ หัวข้อ: สถานการณ์ความมั่นคงในทะเลอันดามัน")
rid = ask("ต่อไป", rid)
```

### 3. แสดงขั้นตอนการทำงานและเวลาของแต่ละขั้น

stream บอกได้ว่าเรียกเครื่องมืออะไร แต่ไม่มีเวลาที่แน่นอนของแต่ละข้อความ
ระหว่างงานยังไม่จบ ให้แอปอ่าน `GET /api/sessions/<session id>/messages` ทุก 3–5 วินาที และอ่านอีกครั้งหลังจบงาน เพื่อได้ `timestamp`, ข้อความคิดของ LLM และผลของเครื่องมือครบทุกขั้น (รูปแบบข้อมูลและวิธีคำนวณเวลาดูใน[การวัดเวลาและค่าใช้จ่ายของแต่ละขั้น](#การวัดเวลาและค่าใช้จ่ายของแต่ละขั้น))
ผลของเครื่องมือในข้อมูลนี้ถูกห่อด้วยแท็ก `<untrusted_tool_result …>` ให้ตัดแท็กออกก่อนแสดงผล

### 4. เปิดไฟล์ที่เอเจนต์เขียน

ไฟล์ของเอเจนต์อยู่ใน `/opt/data/workspace` ภายใน Hermes แอปที่อยู่เครื่องเดียวกันจะ mount `data/workspace` ไว้ก็ได้ แต่แอปที่อยู่คนละเครื่องต้องใช้ API ไฟล์ของ dashboard ซึ่งใช้ได้ทั้งสองกรณี

ขั้นแรกเข้าสู่ระบบ dashboard แล้วเก็บ cookie ไว้ใช้กับทุกคำขอ หากได้ HTTP 401 ภายหลัง ให้เข้าสู่ระบบใหม่แล้วส่งซ้ำ

```json
POST /auth/password-login
{"provider": "basic", "username": "<ชื่อผู้ใช้>", "password": "<รหัสผ่าน>", "next": "/"}
```

| Route | ใช้ทำอะไร |
|---|---|
| `GET /api/files?path=/opt/data/workspace` | รายการไฟล์ในโฟลเดอร์: `entries` มี `name`, `path`, `is_directory`, `size`, `mtime` |
| `GET /api/files/read?path=<path เต็ม>` | อ่านไฟล์: เนื้อหาอยู่ใน `data_url` (`data:<ชนิด>;base64,<เนื้อหา>`) |
| `POST /api/files/upload` `{"path": …, "data_url": …, "overwrite": true}` | เขียนไฟล์ (เนื้อหาเข้ารหัสเป็น `data_url` แบบเดียวกัน) |
| `POST /api/files/mkdir` `{"path": …}` | สร้างโฟลเดอร์ |

path ทุกตัวเป็น path เต็มภายใน Hermes (ขึ้นต้นด้วย `/opt/data/`) API นี้ไม่ยอมให้อ่านไฟล์ค่าลับ เช่น `.env` และ `auth.json`
อย่าส่ง `?profile=` กับ API ไฟล์ เพราะ workspace กลางอยู่นอกโฟลเดอร์ของ profile

### 5. ติดตามงานหลายขั้นของ skill

skill ที่ทำงานเป็นขั้น เช่น `intelligence-analyzer` เขียนผลของทุกขั้นเป็นไฟล์ แอปจึงใช้ไฟล์เหล่านี้บอกความคืบหน้าได้แม่นกว่าการอ่านข้อความตอบ

- แฟ้มงานของแต่ละภารกิจคือโฟลเดอร์ `collection<วันที่>_<เวลา>/` และขั้นที่ทำเสร็จแล้วคือ `step1.md` … `step4.md` ที่มีอยู่
- ปุ่ม "ขั้นต่อไป" ของแอปคือการส่ง `"ต่อไป"` พร้อม `previous_response_id`
- หากเอเจนต์จบรอบโดยยังไม่ได้เขียนไฟล์ของขั้นปัจจุบัน (เช่น ถูกตัดเพราะครบ `agent.max_turns`) แอปส่งคำสั่งให้ทำขั้นนั้นต่อได้ เช่น "ทำขั้นปัจจุบันของแฟ้มงานเดิมให้ครบ" โดยควรจำกัดจำนวนครั้งที่ส่งซ้ำ

### 6. ให้ผู้ใช้ปรับการตั้งค่าของเอเจนต์

ทุก route ในตารางนี้เป็นของ dashboard ให้ต่อท้าย `?profile=osint` เพื่อให้มีผลกับ profile osint (ไม่ใส่ = profile default)

| ต้องการ | Route |
|---|---|
| อ่านการตั้งค่า | `GET /api/config` (`model` ถูกย่อเหลือชื่อ) หรือ `GET /api/config/raw` (ค่า `yaml` คือข้อความตามไฟล์) |
| แก้การตั้งค่าบางส่วน | `PUT /api/config` `{"config": {…เฉพาะส่วนที่แก้…}}` ระบบรวมกับค่าเดิมให้ แต่ค่าที่เป็นรายการจะถูกแทนทั้งรายการ |
| รายการ skill และเปิด/ปิดทีละตัว | `GET /api/skills` และ `PUT /api/skills/toggle` `{"name": …, "enabled": …}` |
| เปิด/ปิด skill ทั้งหมดในครั้งเดียว | `PUT /api/config` `{"config": {"skills": {"disabled": [<ชื่อ skill>, …]}}}` (ส่ง `[]` = เปิดทั้งหมด) เร็วกว่าการสั่งทีละตัวมาก |
| รายการเครื่องมือ | `GET /v1/toolsets` ของ **gateway** (ชุดเครื่องมือที่เอเจนต์ได้รับจริงทาง API) และ `GET /api/mcp/servers` ของ dashboard |
| เปิด/ปิดเครื่องมือหรือ MCP server | `PUT /api/config` `{"config": {"agent": {"disabled_toolsets": [<ชื่อ>, …]}}}` |
| เปลี่ยน model | `POST /api/model/set` `{"scope": "main", "provider": …, "model": …}` (เพิ่ม `base_url` และ `api_key` ได้สำหรับ endpoint ของตัวเอง) |

ทุกการเปลี่ยนแปลงมีผลกับ**บทสนทนาใหม่**เท่านั้น บทสนทนาที่คุยต่อด้วย `previous_response_id` ยังใช้ prompt และรายการเครื่องมือชุดเดิม
เพราะ `PUT /api/config` แทนค่ารายการทั้งรายการ ให้อ่านค่าปัจจุบันก่อนแก้ทุกครั้ง และให้แอปแก้การตั้งค่าครั้งละหนึ่งคำขอเพื่อไม่ให้ทับกัน

### 7. ลบบทสนทนา

| Route (gateway) | ลบอะไร |
|---|---|
| `DELETE /v1/responses/<response id>` | บทสนทนาที่เก็บไว้สำหรับ `previous_response_id` (ลบทุก `id` ของบทสนทนานั้น) |
| `DELETE /api/sessions/<session id>` | เซสชันและขั้นตอนทั้งหมด (Hermes ไม่ยอมลบระหว่างที่เซสชันกำลังทำงาน) |

ไฟล์ใน workspace ไม่ถูกลบตามไปด้วย

### 8. รวบรวมข้อมูลการใช้งาน

แอปผูกข้อมูลการใช้งานของทุกกระบวนการเข้ากับคำสั่งของตัวเองได้ ด้วย id ที่ได้ตอนสั่งงาน (ดู[ข้อมูลการใช้งานสำหรับงานวิจัย](#ข้อมูลการใช้งานสำหรับงานวิจัย))

1. อ่านไฟล์ของ plugin ผ่าน API ไฟล์ของ dashboard: `GET /api/files?path=/opt/data/profiles/osint/logs/usage` แล้วอ่านไฟล์ของวันที่ต้องการ
2. อ่าน `GET /usage?since=<epoch>&until=<epoch>` ของ MCP server แต่ละตัว
3. เชื่อมโยง
   - ระเบียนของ Hermes ใช้ `session_id` เดียวกับ header `X-Hermes-Session-Id` และเวลาอยู่ในช่วงของคำสั่ง
   - ระเบียนของ MCP ใช้ชื่อเครื่องมือ (`tool_call` ของ Hermes ชื่อ `mcp__<server>__<tool>`) และเวลาที่อยู่ภายในการเรียกเครื่องมือครั้งนั้น
   - การเรียก LLM ของ MCP ใช้ `request_id` เดียวกับระเบียน `mcp_tool` ของมัน

collector ทำทั้งหมดนี้ให้แล้ว: หน้าจอแสดง token ของแต่ละคำสั่ง และปุ่ม Export Usage (ZIP) ส่งออก `records.jsonl`, `records.csv`, `runs.csv` (สรุปต่อคำสั่ง) และ `manifest.json` (สภาพแวดล้อมของทุกเครื่อง)

### เช็กลิสต์ก่อนใช้งานจริง

- เก็บ `API_SERVER_KEY` และรหัสผ่าน dashboard ไว้ฝั่ง server ของแอปเท่านั้น ห้ามส่งให้เว็บเบราว์เซอร์ เพราะผู้ที่มี key นี้สั่งเอเจนต์ใช้ `terminal` ได้
- ให้แอปมีระบบเข้าสู่ระบบของผู้ใช้เอง แล้วแอปเป็นผู้เรียก Hermes แทนผู้ใช้
- ตั้งเวลาสูงสุดต่อคำสั่ง และแสดงสถานะ "ยังไม่เสร็จ" แทนการรอไม่สิ้นสุด
- เก็บ `id` ของคำตอบและเซสชันไว้ในฐานข้อมูลของแอป เพื่อเปิดบทสนทนาเดิมและลบได้ภายหลัง
- ทดสอบกับคำสั่งสั้น ๆ ก่อน เช่น "สวัสดี" แล้วจึงทดสอบโหมดนักวิเคราะห์ เพราะแต่ละขั้นใช้ token หลายหมื่น

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
