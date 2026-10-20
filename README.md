# harness-server

เอเจนต์ AI สำหรับงานข่าวกรองจากแหล่งข้อมูลเปิด (OSINT) ที่สร้างบน [Hermes Agent](https://github.com/NousResearch/hermes-agent) พร้อมบุคลิก กฎการทำงาน และ skill นักวิเคราะห์ข่าวกรอง
ติดตั้งเป็น **profile ของ Hermes ชื่อ `osint`** ด้วยคำสั่งเดียว และให้บริการ API แบบ OpenAI-compatible แก่แอปอื่น โดยเชื่อมต่อเครื่องมือผ่าน MCP ได้แก่ Perplexity, ตรวจคำสะกดภาษาไทย และคลังความรู้ LightRAG

ผู้พัฒนา: **Chacharin Lertyosbordin**

> โปรเจกต์นี้คือการตั้งค่าและเนื้อหาของเอเจนต์ (SOUL และ skill) ที่ใช้กับ Hermes Agent ไม่ได้รวมตัว Hermes มาด้วย
> Hermes Agent พัฒนาโดย Nous Research ภายใต้สัญญาอนุญาต MIT และโปรเจกต์นี้ไม่ใช่ผลงานทางการของ Nous Research

## องค์ประกอบ

repo นี้เป็น **Hermes profile distribution** คำสั่ง `hermes profile install` จะคัดลอกเฉพาะ 4 รายการแรกเข้าไปใน profile

| ไฟล์ | หน้าที่ |
|---|---|
| `SOUL.md` | บุคลิกและกฎการทำงานของเอเจนต์ |
| `skills/intelligence/` | skill `intelligence-analyzer` โหมดนักวิเคราะห์ข่าวกรองแบบ 4 ขั้นตอน (STEEP) |
| `config.yaml` | ค่าที่ต่างจากค่าเริ่มต้นของ Hermes ได้แก่ model, โฟลเดอร์ทำงาน, เครื่องมือ และ MCP server |
| `.env.template` | ค่าลับที่ profile ต้องมี (Hermes ติดตั้งไว้เป็น `.env.EXAMPLE`) |
| `distribution.yaml` | ชื่อ เวอร์ชัน เวอร์ชันของ Hermes ที่ต้องใช้ และรายการไฟล์ที่ติดตั้ง |
| `docker-compose.yml`, `.env.example` | ชุดติดตั้ง Hermes บน Docker (gateway และ dashboard) สำหรับผู้ที่ยังไม่มี Hermes |

ชื่อ profile ใน Hermes เป็นตัวพิมพ์เล็กเสมอ จึงใช้ชื่อ `osint`

## หลักการทำงาน

```
แอปที่เรียกเอเจนต์ ──POST /p/osint/v1/responses──▶ hermes (gateway เดียวของเครื่อง)
                                                  ① เลือก profile osint จาก path /p/osint
                                                  ② ตรวจ API_SERVER_KEY ของ profile osint
                                                  ③ ใส่ SOUL.md และรายการ skill ของ osint ลงใน prompt
                                                  ④ LLM (ผ่าน OpenRouter) คิดและเลือกเครื่องมือ
                                                     ├─ เครื่องมือของ Hermes: web_search, write_file, terminal …
                                                     └─ MCP: mcp-perplexity, mcp-thai-proofread, mcp-lightrag
                                                ◀── ส่งคำตอบกลับ (หรือส่งทีละส่วนแบบ stream)

ผู้ดูแลระบบ ──http://<เครื่อง>:9119──▶ hermes-dashboard (ตั้งค่า ดูบทสนทนา และแชทกับเอเจนต์ ทุก profile)
```

Hermes 0.21 ให้มี gateway เพียงตัวเดียวต่อเครื่อง คือ gateway ของ profile `default` ซึ่งให้บริการทุก profile ผ่าน path `/p/<profile>/` profile osint จึงไม่ต้องเปิด gateway ของตัวเอง

**ไฟล์ของ profile** อยู่ที่ `data/profiles/osint/` (ใน container คือ `/opt/data/profiles/osint/`) ได้แก่ SOUL, config, skill, `.env`, บทสนทนา และความจำของเอเจนต์ แยกจาก profile อื่นทั้งหมด

**โฟลเดอร์ทำงานกลาง** คือ `data/workspace/` (`/opt/data/workspace`) ซึ่ง `config.yaml` กำหนดไว้ใน `terminal.cwd` แฟ้มงานของ `intelligence-analyzer` (`collection…/step1.md` ถึง `step4.md`) รายงาน และไฟล์ที่บันทึกตามกฎข้อ 3 อยู่ที่นี่ทั้งหมด MCP ที่แก้ไฟล์ (mcp-thai-proofread) และแอปที่อ่านไฟล์ต้อง mount โฟลเดอร์เดียวกันนี้ และต้องอยู่เครื่องเดียวกับ Hermes

## เริ่มต้นใช้งาน

### สิ่งที่ต้องเตรียม

- **Hermes Agent เวอร์ชัน 0.21.6 ขึ้นไป** ถ้ายังไม่มี ใช้ `docker-compose.yml` ใน repo นี้ได้ (ดูหัวข้อถัดไป)
- **OpenRouter API key** ขอได้ที่ https://openrouter.ai/keys
- **MCP server ทั้ง 3 ตัว** ที่ทำงานอยู่ใน docker network เดียวกับ Hermes หากยังไม่มี ให้ติดตั้งตาม README ของแต่ละตัว
  - [mcp-perplexity](https://github.com/chacharin/mcp-perplexity) ค้นหาเว็บและถามตอบผ่าน Perplexity
  - [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) ตรวจและแก้คำสะกดภาษาไทย (ต้อง mount `data/workspace` ของ Hermes)
  - [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) คลังความรู้ LightRAG

  เอเจนต์ยังทำงานได้แม้ขาด MCP server บางตัว เพียงแต่จะไม่มีเครื่องมือของตัวนั้น

### ติดตั้ง Hermes บน Docker (ข้ามได้ถ้ามี Hermes อยู่แล้ว)

```bash
git clone https://github.com/chacharin/harness-server.git
cd harness-server
docker network create agent_network   # สร้างครั้งแรกครั้งเดียว หากต้องการใช้ชื่ออื่นให้กำหนดใน DOCKER_NETWORK
docker compose up -d                  # ครั้งแรก Hermes จะสร้างโฟลเดอร์ data/ เอง
```

ค่าของ docker compose เช่น พอร์ตของ dashboard ปรับได้ด้วยการคัดลอก [`.env.example`](.env.example) เป็น `.env` แล้วสั่ง `docker compose up -d` อีกครั้ง

### ติดตั้ง profile osint

```bash
docker exec -u hermes hermes hermes profile install github.com/chacharin/harness-server -y
```

(ถ้าติดตั้ง Hermes แบบปกติ ไม่ใช่ Docker ให้สั่ง `hermes profile install github.com/chacharin/harness-server`)

จากนั้นสร้าง `.env` ของ profile จาก `.env.EXAMPLE` ที่ Hermes ติดตั้งให้ แล้วใส่ค่าจริง 2 ค่า (ดู [`.env.template`](.env.template))

```bash
cp data/profiles/osint/.env.EXAMPLE data/profiles/osint/.env   # แล้วแก้ OPENROUTER_API_KEY และ API_SERVER_KEY
```

gateway จะค้นพบ profile ใหม่เองภายในไม่เกิน 30 วินาที ตรวจสถานะได้ด้วย

```bash
docker exec hermes hermes profile list
docker exec hermes curl -s http://127.0.0.1:8642/p/osint/v1/models -H "Authorization: Bearer <API_SERVER_KEY ของ osint>"
```

หากได้รายการ model ที่มี `"id": "osint"` แปลว่าพร้อมใช้งาน log ของ profile อยู่ที่ `data/profiles/osint/logs/` และควรเห็นข้อความ `MCP: registered … into this profile scope`

### การตั้งรหัสผ่าน dashboard

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

เปิด `http://127.0.0.1:9119` หรือ `http://<IP ของเครื่อง>:9119` จากเครื่องอื่น แล้วเข้าสู่ระบบด้วยชื่อผู้ใช้และรหัสผ่านนี้
หากกำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1` จะเปิดได้เฉพาะเครื่องนี้ และไม่ต้องตั้งรหัสผ่าน

### การเชื่อมต่อจากแอปอื่น

แอปที่อยู่ใน docker network เดียวกันเรียก API ของเอเจนต์ osint ได้ที่ `http://hermes:8642/p/osint/v1` โดยส่ง header `Authorization: Bearer <API_SERVER_KEY ของ osint>`
พอร์ต 8642 ไม่ได้เปิดออกนอก docker network แอปที่อยู่นอก network ต้องเชื่อมผ่าน HTTPS (reverse proxy) หรือเครือข่ายส่วนตัว

ตัวอย่างการตั้งค่าในแอปที่ใช้ไลบรารีของ OpenAI:

```python
from openai import OpenAI
client = OpenAI(base_url="http://hermes:8642/p/osint/v1", api_key="<API_SERVER_KEY ของ osint>")
reply = client.responses.create(model="osint", input="สรุปข่าวเด่นวันนี้")
print(reply.output_text)
```

แอปที่ตั้งค่าที่อยู่ของเอเจนต์และชื่อ profile แยกกัน ให้ใช้ที่อยู่ `http://hermes:8642/p/osint` และชื่อ profile (model) `osint`

## วิธีใช้งาน

ผู้ใช้สั่งเอเจนต์ด้วยภาษาปกติผ่านแอปหรือ dashboard เอเจนต์จะทำตามกฎใน SOUL และเลือกเครื่องมือให้เอง
หัวข้อนี้อธิบายว่าแต่ละงานควรสั่งอย่างไร และเอเจนต์จะใช้เครื่องมือใด

### 1. โหมดนักวิเคราะห์ข่าวกรอง

ตัวอย่างคำสั่ง:

> ทำหน้าที่เป็นนักวิเคราะห์ หัวข้อ: สถานการณ์ความมั่นคงในทะเลอันดามัน
> act as an intelligence analyst. Topic: …

เอเจนต์จะโหลด skill `intelligence-analyzer` (กฎข้อ 1) แล้วทำงานทีละขั้น และรอคำสั่งก่อนขึ้นขั้นถัดไป

| ขั้น | งาน | ไฟล์ที่ได้ใน workspace |
|---|---|---|
| 1 | สำรวจและรวบรวมข้อมูลเชิงยุทธศาสตร์ | สร้างแฟ้มงาน `collection…/` และ `step1.md` |
| 2 | ประเมินความน่าเชื่อถือของแหล่งข้อมูล | `step2.md` |
| 3 | วิเคราะห์ด้วยกรอบ STEEP (สังคม เทคโนโลยี เศรษฐกิจ สิ่งแวดล้อม การเมือง) | `step3.md` |
| 4 | เขียนรายงานสำหรับผู้บริหาร | `step4.md` และ `report_<วันที่>_<เวลา>.md` |

ทุกขั้นตรวจคำสะกดภาษาไทยของไฟล์ที่เขียนด้วย `proofread_thai` เมื่อส่งรายงานขั้นที่ 4 แล้ว เอเจนต์จะออกจากโหมดนักวิเคราะห์ และกลับมาตอบแบบแชทปกติ

### 2. ค้นหาข้อมูลบนเว็บ

ตัวอย่างคำสั่ง:

> ค้นหาข่าวล่าสุดเกี่ยวกับนโยบาย AI ของไทย

เมื่อผู้ใช้สั่ง "ค้นหา" เอเจนต์จะใช้เครื่องมือ `web_search` ของ Hermes ทันที (กฎข้อ 2)
หากต้องการคำตอบที่สรุปพร้อมแหล่งอ้างอิง หรือการค้นคว้าเชิงลึก ให้ระบุว่าใช้ Perplexity เช่น "ถาม Perplexity ว่า …" หรือ "ค้นคว้าเชิงลึกด้วย Perplexity เรื่อง …"

### 3. บันทึกผลงานเป็นไฟล์

ตัวอย่างคำสั่ง:

> บันทึกสรุปนี้ไว้
> จัดเก็บรายงานนี้เป็นไฟล์ .md

เอเจนต์จะสร้างไฟล์ใน workspace กลาง (`data/workspace/` บนเครื่อง) โดยตั้งชื่อไฟล์ตามเนื้อหาและใส่วันเวลากำกับไว้ (กฎข้อ 3) หากไม่ระบุชนิดไฟล์ จะบันทึกเป็น `.txt`

### 4. ใช้งานคลังความรู้

ตัวอย่างคำสั่ง:

> ค้นจากคลังความรู้ว่าเคยมีรายงานเรื่อง … หรือไม่
> เก็บรายงานนี้เข้าคลังความรู้ โดยตั้งชื่อว่า …
> ในคลังความรู้มีเอกสารอะไรบ้าง

เอเจนต์จะใช้เครื่องมือของ [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) ได้แก่ `lightrag_query`, `lightrag_insert` และ `lightrag_list_documents`

### 5. ตรวจคำสะกดภาษาไทย

ตัวอย่างคำสั่ง:

> ตรวจคำสะกดภาษาไทยในไฟล์ report.md ให้หน่อย

เอเจนต์จะใช้เครื่องมือของ [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) แก้ไฟล์ใน workspace โดยสำรองไฟล์ต้นฉบับไว้ก่อนเสมอ

## รูปแบบ JSON ของคำขอและผลลัพธ์

API ของเอเจนต์เป็นแบบ OpenAI-compatible ทุก route ของ profile osint ขึ้นต้นด้วย `/p/osint`

| Route | ใช้ทำอะไร | ต้องใช้ key |
|---|---|---|
| `POST /p/osint/v1/responses` | สั่งงานเอเจนต์และรับคำตอบ (Responses API) | ✓ |
| `GET /p/osint/v1/models` | ดูรายชื่อ model ที่เรียกได้ | ✓ |
| `GET /p/osint/v1/toolsets` | ดูชุดเครื่องมือที่เอเจนต์ได้รับ พร้อมสถานะเปิด/ปิด | ✓ |
| `GET /p/osint/api/sessions/<id>/messages` | ขั้นตอนการทำงานของบทสนทนา พร้อมเวลาของแต่ละขั้น | ✓ |
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
| `previous_response_id` | (ไม่บังคับ) `id` ของคำตอบก่อนหน้า เพื่อคุยต่อในบทสนทนาเดิม |

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

คำตอบของเอเจนต์อยู่ใน `output` รายการที่มี `"type": "message"` header `X-Hermes-Session-Id` ของผลลัพธ์คือรหัสบทสนทนา ใช้ดึงขั้นตอนการทำงานจาก `/p/osint/api/sessions/<id>/messages` หรือเปิดดูใน dashboard ได้

`usage.input_tokens` นับรวมทุกรอบที่เอเจนต์เรียก LLM ตัวอย่างนี้เรียกเครื่องมือ 1 ครั้ง จึงส่ง prompt 2 รอบ (รอบละประมาณ 13,000 token ซึ่งส่วนใหญ่เป็นคำอธิบายเครื่องมือ) ใช้เวลารวมประมาณ 9 วินาที

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

## การปรับให้เหมาะกับงานของคุณ

ค่าต่อไปนี้อยู่ในโฟลเดอร์ของ profile (`data/profiles/osint/`) แก้ได้โดยตรงหรือผ่าน dashboard เมื่อแก้ไขแล้วมีผลกับบทสนทนาใหม่

- **`SOUL.md`** บุคลิกและกฎการทำงาน เขียนเป็นภาษาปกติได้เลย เช่น เพิ่มกฎว่าเมื่อผู้ใช้สั่งคำใดให้ใช้เครื่องมือใด
- **`skills/`** เพิ่ม skill ของตัวเองเป็นโฟลเดอร์ที่มีไฟล์ `SKILL.md` (ดูตัวอย่างจาก `intelligence-analyzer`)
- **`model` ใน `config.yaml`** เปลี่ยน LLM ของเอเจนต์ ควรเลือก model ที่รองรับภาษาไทยและการเรียกใช้เครื่องมือได้ดี
- **`agent.max_turns` ใน `config.yaml`** จำนวนรอบเรียกเครื่องมือสูงสุดต่อหนึ่งคำสั่ง เพิ่มได้หากงานวิเคราะห์ยาวถูกตัดกลางคัน
- **`mcp_servers` ใน `config.yaml`** เพิ่มหรือถอด MCP server

**skill มาตรฐานของ Hermes** profile ที่ติดตั้งใหม่มีเฉพาะ `intelligence-analyzer` จึงใช้ token น้อยกว่า profile default ประมาณ 1,300 token ต่อรอบ หากต้องการ skill มาตรฐานทั้งหมดของ Hermes ด้วย ให้สั่ง

```bash
docker exec -u hermes hermes hermes -p osint skills opt-in --sync
```

**อัปเดตเอเจนต์เป็นเวอร์ชันใหม่ของ repo นี้**

```bash
docker exec -u hermes hermes hermes profile update osint
```

`SOUL.md` และ `skills/` จะถูกแทนที่ด้วยเวอร์ชันใหม่ ส่วน `config.yaml`, `.env`, บทสนทนา และความจำของเอเจนต์คงไว้ตามเดิม

## ความปลอดภัย

- **API ของเอเจนต์** (พอร์ต 8642) เปิดเฉพาะภายใน docker network และต้องใช้ `API_SERVER_KEY` ของแต่ละ profile ทุกครั้ง
  ผู้ที่มี key นี้สั่งเอเจนต์ใช้ทุกเครื่องมือได้ รวมถึง `terminal` ที่รันคำสั่งใน container ของ Hermes โดยตรง จึงต้องเก็บ key เป็นความลับ และให้เฉพาะแอปที่ไว้ใจได้
- **dashboard** (พอร์ต 9119) เปิดให้เครื่องอื่นในเครือข่ายเข้าถึงได้เป็นค่าเริ่มต้น (`DASHBOARD_PUBLISH_ADDR=0.0.0.0`) และต้องเข้าสู่ระบบด้วยรหัสผ่านที่ตั้งไว้ทุกครั้ง หากไม่จำเป็น ให้กำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1`
- **ค่าลับทั้งหมด** อยู่ใน `.env` ของแต่ละ profile, `data/auth.json` และรหัสผ่าน dashboard ใน `data/config.yaml` ซึ่ง `.gitignore` กันไม่ให้ขึ้น git ทั้งโฟลเดอร์ `data/`
- ควรตั้งวงเงินของ OpenRouter API key ไว้ เพื่อจำกัดค่าใช้จ่ายหากเอเจนต์ทำงานวนนานผิดปกติ

## สำหรับนักพัฒนา

### ทดลองติดตั้งจากเครื่องก่อน push

`hermes profile install` รับโฟลเดอร์ที่มี `distribution.yaml` ได้ด้วย ส่งออกเฉพาะไฟล์ที่ git ติดตามไปไว้ใน `data/` (ไม่รวม `data/` เอง) แล้วติดตั้งจากที่นั่น

```bash
git checkout-index -a --prefix=data/.dist-osint/
docker exec -u hermes hermes hermes profile install /opt/data/.dist-osint --force -y
```

`--force` ใช้แทนที่ profile เดิม: `SOUL.md`, `skills/` และ `config.yaml` จะถูกแทนที่ด้วยของ repo ส่วน `.env`, บทสนทนา และความจำคงไว้ เสร็จแล้วลบ `data/.dist-osint/` ได้

### การอัปเดตเวอร์ชันของ Hermes

ชุดติดตั้งนี้ล็อก image ไว้ที่ `nousresearch/hermes-agent:v0.21.6` หากต้องการอัปเดต ให้กำหนด `HERMES_IMAGE` ในไฟล์ `.env` แล้วสั่ง

```bash
docker compose pull
docker compose up -d
```

จากนั้นตรวจว่า `/health` แสดงเวอร์ชันใหม่ log ของ profile osint แสดง `MCP: registered` และโหมดนักวิเคราะห์ยังทำงานได้ ก่อนแก้ `hermes_requires` ใน `distribution.yaml` และค่าเริ่มต้นใน `docker-compose.yml`
ถ้า Hermes เวอร์ชันใหม่เปลี่ยนรูปแบบ config ให้ปรับ `_config_version` ใน `config.yaml` ตามค่าใน `data/config.yaml` ที่ Hermes สร้างใหม่

## สัญญาอนุญาต

[MIT](LICENSE) © 2026 Chacharin Lertyosbordin
Hermes Agent เป็นลิขสิทธิ์ของ Nous Research ภายใต้สัญญาอนุญาต MIT ([ซอร์สโค้ด](https://github.com/NousResearch/hermes-agent))
