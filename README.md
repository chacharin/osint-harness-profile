# harness-server

เอเจนต์ AI สำหรับงานข่าวกรองจากแหล่งข้อมูลเปิด (OSINT) ที่สร้างบน [Hermes Agent](https://github.com/NousResearch/hermes-agent) พร้อมบุคลิก กฎการทำงาน และ skill นักวิเคราะห์ข่าวกรอง
ทำงานบน Docker และให้บริการ API แบบ OpenAI-compatible แก่แอปอื่น โดยเชื่อมต่อเครื่องมือผ่าน MCP ได้แก่ Perplexity, ตรวจคำสะกดภาษาไทย และคลังความรู้ LightRAG

ผู้พัฒนา: **Chacharin Lertyosbordin**

> โปรเจกต์นี้คือการตั้งค่าและเนื้อหาของเอเจนต์ (SOUL และ skill) ที่ใช้กับ Hermes Agent ไม่ได้รวมตัว Hermes มาด้วย
> Hermes Agent พัฒนาโดย Nous Research ภายใต้สัญญาอนุญาต MIT และโปรเจกต์นี้ไม่ใช่ผลงานทางการของ Nous Research

## องค์ประกอบ

| ไฟล์ | หน้าที่ |
|---|---|
| `data/SOUL.md` | บุคลิกและกฎการทำงานของเอเจนต์ |
| `data/skills/intelligence/` | skill `intelligence-analyzer` โหมดนักวิเคราะห์ข่าวกรองแบบ 4 ขั้นตอน (STEEP) |
| `config.yaml.example` | ค่าที่ต้องตั้งใน `data/config.yaml` ได้แก่ model, เครื่องมือ และ MCP server |
| `hermes.env.example` | ค่าลับที่ต้องมีใน `data/.env` ได้แก่ OpenRouter API key และ key ของ API เอเจนต์ |
| `docker-compose.yml`, `.env.example` | ติดตั้ง Hermes (gateway และ dashboard) และค่าที่ปรับได้ |

นอกจาก skill ของเราแล้ว เอเจนต์ยังใช้ skill และเครื่องมือมาตรฐานที่มากับ Hermes ได้ทั้งหมด เช่น ค้นเว็บ อ่านและเขียนไฟล์ จำข้อมูลข้ามบทสนทนา และเปิดเว็บด้วย browser

## หลักการทำงาน

```
แอปที่เรียกเอเจนต์ ──POST /v1/responses──▶ hermes (gateway)
                                         ① ตรวจ API_SERVER_KEY
                                         ② ใส่ SOUL.md และรายการ skill ลงใน prompt
                                         ③ LLM (ผ่าน OpenRouter) คิดและเลือกเครื่องมือ
                                            ├─ เครื่องมือของ Hermes: web_search, file, terminal, memory …
                                            └─ MCP: mcp-perplexity, mcp-thai-proofread, mcp-lightrag
                                       ◀── ส่งคำตอบกลับ (หรือส่งทีละส่วนแบบ stream)

ผู้ดูแลระบบ ──http://<เครื่อง>:9119──▶ hermes-dashboard (ตั้งค่า ดูบทสนทนา และแชทกับเอเจนต์)
```

Hermes เก็บทุกอย่างไว้ในโฟลเดอร์ `data/` ได้แก่ การตั้งค่า, ค่าลับ, บทสนทนา, ความจำของเอเจนต์ และไฟล์ที่เอเจนต์บันทึก (`data/workspace/`)
ค่าใช้จ่ายหลักคือ LLM ซึ่งคิดตาม token ของทุกคำสั่ง เนื่องจาก SOUL และรายการ skill ถูกใส่ใน prompt ทุกครั้ง คำถามสั้น ๆ จึงใช้ input ประมาณ 15,000 token

## เริ่มต้นใช้งาน

### สิ่งที่ต้องเตรียม

- **Docker** (Docker Desktop หรือ Docker Engine)
- **OpenRouter API key** ขอได้ที่ https://openrouter.ai/keys
- **MCP server ทั้ง 3 ตัว** ที่ทำงานอยู่ใน docker network เดียวกัน หากยังไม่มี ให้ติดตั้งตาม README ของแต่ละตัว
  - [mcp-perplexity](https://github.com/chacharin/mcp-perplexity) ค้นหาเว็บและถามตอบผ่าน Perplexity
  - [mcp-thai-proof-md](https://github.com/chacharin/mcp-thai-proof-md) ตรวจและแก้คำสะกดภาษาไทย
  - [mcp-lightrag](https://github.com/chacharin/mcp-lightrag) คลังความรู้ LightRAG

  เอเจนต์ยังทำงานได้แม้ขาด MCP server บางตัว เพียงแต่จะไม่มีเครื่องมือของตัวนั้น

### ขั้นตอนการติดตั้ง

```bash
git clone https://github.com/chacharin/harness-server.git
cd harness-server
docker network create agent_network   # สร้างครั้งแรกครั้งเดียว หากต้องการใช้ชื่ออื่นให้กำหนดใน DOCKER_NETWORK
docker compose up -d                  # ครั้งแรก Hermes จะสร้าง data/config.yaml และ data/.env เอง
docker compose stop gateway
```

จากนั้นตั้งค่า 2 ไฟล์ที่ Hermes สร้างขึ้น

1. **`data/.env`** ใส่ `OPENROUTER_API_KEY` และจดค่า `API_SERVER_KEY` ไว้ให้แอปที่จะเรียกเอเจนต์ (ดู [`hermes.env.example`](hermes.env.example))
2. **`data/config.yaml`** นำค่าจาก [`config.yaml.example`](config.yaml.example) ไปแทนค่าเดิมในหัวข้อเดียวกัน ได้แก่ `model`, `agent.max_turns`, `terminal.cwd`, `platform_toolsets`, `browser`, `computer_use` และ `mcp_servers`

แล้วเปิด gateway และตรวจสถานะ:

```bash
docker compose up -d
docker exec hermes curl -s http://127.0.0.1:8642/health
docker exec hermes grep "MCP: registered" /opt/data/logs/agent.log
```

หาก `/health` ตอบ `"status": "ok"` และ log แสดง `MCP: registered … from 3 server(s)` แปลว่าเอเจนต์พร้อมใช้งานและเชื่อมต่อ MCP ได้ครบ
`data/SOUL.md` และ `data/skills/intelligence/` มาพร้อมกับ repo นี้แล้ว Hermes จะอ่านทุกครั้งที่ gateway เริ่มทำงาน

หากต้องการปรับค่าของ docker compose เช่น พอร์ตของ dashboard ให้คัดลอก [`.env.example`](.env.example) เป็น `.env` แล้วแก้เฉพาะค่าที่ต้องการ จากนั้นสั่ง `docker compose up -d`

### การตั้งรหัสผ่าน dashboard

dashboard ที่เปิดให้เครื่องอื่นเข้าถึงได้ (`DASHBOARD_PUBLISH_ADDR=0.0.0.0`) จะไม่เริ่มทำงานจนกว่าจะตั้งรหัสผ่าน ให้สร้าง hash ของรหัสผ่านด้วยคำสั่ง

```bash
docker exec -w /opt/hermes hermes /opt/hermes/.venv/bin/python -c   "from plugins.dashboard_auth.basic import hash_password; print(hash_password('<รหัสผ่าน>'))"
```

แล้วเพิ่มในหัวข้อ `dashboard` ของ `data/config.yaml` จากนั้นสั่ง `docker compose restart dashboard`

```yaml
dashboard:
  basic_auth:
    username: admin
    password_hash: scrypt$16384$8$1$…   # ค่าที่ได้จากคำสั่งข้างต้น
```

เปิด `http://127.0.0.1:9119` หรือ `http://<IP ของเครื่อง>:9119` จากเครื่องอื่น แล้วเข้าสู่ระบบด้วยชื่อผู้ใช้และรหัสผ่านนี้
หากกำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1` จะเปิดได้เฉพาะเครื่องนี้ และไม่ต้องตั้งรหัสผ่าน

### การเชื่อมต่อจากแอปอื่น

แอปที่อยู่ใน docker network เดียวกันเรียก API ของเอเจนต์ได้ที่ `http://hermes:8642/v1` โดยส่ง header `Authorization: Bearer <API_SERVER_KEY>`
พอร์ต 8642 ไม่ได้เปิดออกนอก docker network แอปที่อยู่นอก network จึงเรียกโดยตรงไม่ได้

ตัวอย่างการตั้งค่าในแอปที่ใช้ไลบรารีของ OpenAI:

```python
from openai import OpenAI
client = OpenAI(base_url="http://hermes:8642/v1", api_key="<API_SERVER_KEY>")
reply = client.responses.create(model="default", input="สรุปข่าวเด่นวันนี้")
print(reply.output_text)
```

## วิธีใช้งาน

ผู้ใช้สั่งเอเจนต์ด้วยภาษาปกติผ่านแอปหรือ dashboard เอเจนต์จะทำตามกฎใน SOUL และเลือกเครื่องมือให้เอง
หัวข้อนี้อธิบายว่าแต่ละงานควรสั่งอย่างไร และเอเจนต์จะใช้เครื่องมือใด

### 1. โหมดนักวิเคราะห์ข่าวกรอง

ตัวอย่างคำสั่ง:

> ทำหน้าที่เป็นนักวิเคราะห์ หัวข้อ: สถานการณ์ความมั่นคงในทะเลอันดามัน
> act as an intelligence analyst. Topic: …

เอเจนต์จะโหลด skill `intelligence-analyzer` (กฎข้อ 1) แล้วทำงานทีละขั้นตามลำดับ

| ขั้น | งาน |
|---|---|
| 1 | สำรวจและรวบรวมข้อมูลเชิงยุทธศาสตร์ |
| 2 | ประเมินความน่าเชื่อถือของแหล่งข้อมูล |
| 3 | วิเคราะห์ด้วยกรอบ STEEP (สังคม เทคโนโลยี เศรษฐกิจ สิ่งแวดล้อม การเมือง) |
| 4 | เขียนรายงานสำหรับผู้บริหาร |

เมื่อส่งรายงานขั้นที่ 4 แล้ว เอเจนต์จะออกจากโหมดนักวิเคราะห์ และกลับมาตอบแบบแชทปกติ
หากผู้ใช้ยังไม่ได้ให้หัวข้อ เอเจนต์จะตอบรับและรอรับภารกิจก่อน

### 2. ค้นหาข้อมูลบนเว็บ

ตัวอย่างคำสั่ง:

> ค้นหาข่าวล่าสุดเกี่ยวกับนโยบาย AI ของไทย

เมื่อผู้ใช้สั่ง "ค้นหา" เอเจนต์จะใช้เครื่องมือ `web_search` ของ Hermes ทันที (กฎข้อ 2)
หากต้องการคำตอบที่สรุปพร้อมแหล่งอ้างอิง หรือการค้นคว้าเชิงลึก ให้ระบุว่าใช้ Perplexity เช่น "ถาม Perplexity ว่า …" หรือ "ค้นคว้าเชิงลึกด้วย Perplexity เรื่อง …"

### 3. บันทึกผลงานเป็นไฟล์

ตัวอย่างคำสั่ง:

> บันทึกสรุปนี้ไว้
> จัดเก็บรายงานนี้เป็นไฟล์ .md

เอเจนต์จะสร้างไฟล์ใน workspace (`data/workspace/` บนเครื่อง) โดยตั้งชื่อไฟล์ตามเนื้อหาและใส่วันเวลากำกับไว้ (กฎข้อ 3)
หากไม่ระบุชนิดไฟล์ จะบันทึกเป็น `.txt`

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

API ของเอเจนต์เป็นแบบ OpenAI-compatible ซึ่งมี route หลักดังนี้

| Route | ใช้ทำอะไร | ต้องใช้ key |
|---|---|---|
| `POST /v1/responses` | สั่งงานเอเจนต์และรับคำตอบ (Responses API) | ✓ |
| `GET /v1/models` | ดูรายชื่อ model ที่เรียกได้ | ✓ |
| `GET /health` | ตรวจว่า gateway ทำงานอยู่ | |

ทุกคำขอที่ต้องใช้ key ต้องส่ง header `Authorization: Bearer <API_SERVER_KEY>`

### สั่งงานเอเจนต์ (`POST /v1/responses`)

คำขอ:

```json
{"model": "default", "input": "ตอบสั้น ๆ ประโยคเดียว: วันนี้คุณพร้อมทำงานไหม", "stream": false}
```

| ค่า | ความหมาย |
|---|---|
| `model` | ชื่อ profile ของ Hermes ที่จะใช้ (`default`) ส่วน model ของ LLM กำหนดใน `data/config.yaml` |
| `input` | คำสั่งหรือคำถาม |
| `stream` | `true` = ส่งผลลัพธ์ทีละส่วนแบบ Server-Sent Events ระหว่างที่เอเจนต์ทำงาน เหมาะกับงานที่ใช้เวลานาน |
| `previous_response_id` | (ไม่บังคับ) `id` ของคำตอบก่อนหน้า เพื่อคุยต่อในบทสนทนาเดิม |

ผลลัพธ์ (ย่อ):

```json
{
  "id": "resp_5a777c19dcea4b599ba3edd45840",
  "object": "response",
  "status": "completed",
  "model": "default",
  "output": [
    {"type": "reasoning", "summary": [{"type": "summary_text", "text": "…"}]},
    {"type": "message", "role": "assistant",
     "content": [{"type": "output_text", "text": "พร้อมครับ พร้อมลุยงานเต็มที่เลยครับ"}]}
  ],
  "usage": {"input_tokens": 14639, "output_tokens": 187, "total_tokens": 14826}
}
```

คำตอบของเอเจนต์อยู่ใน `output` รายการที่มี `"type": "message"` เมื่อเอเจนต์เรียกเครื่องมือ `output` จะมีรายการ `function_call` และ `function_call_output` ด้วย
header `X-Hermes-Session-Id` ของผลลัพธ์คือรหัสบทสนทนา ซึ่งใช้เปิดดูรายละเอียดใน dashboard ได้

### ข้อผิดพลาด

| กรณี | ผลลัพธ์ |
|---|---|
| ไม่ส่ง key หรือ key ผิด | HTTP 401 `{"error": {"message": "Invalid gateway API key (API_SERVER_KEY)", "type": "gateway_auth_error", "code": "gateway_auth_failed"}}` |
| OpenRouter API key ผิดหรือวงเงินหมด | คำตอบแจ้งข้อผิดพลาดจาก OpenRouter ให้ตรวจ `OPENROUTER_API_KEY` และวงเงินที่ https://openrouter.ai/settings/credits |
| MCP server ตัวใดไม่ทำงาน | เอเจนต์ยังทำงานได้ แต่ไม่มีเครื่องมือของตัวนั้น ตรวจได้จาก log `MCP: registered` |

### ตรวจสถานะ (`GET /health`)

```json
{"status": "ok", "platform": "hermes-agent", "version": "0.21.6"}
```

### ทดลองด้วย curl

พอร์ต 8642 อยู่ภายใน docker network จึงต้องเรียกจาก container ที่อยู่ใน network เดียวกัน เช่น

```bash
docker run --rm --network agent_network curlimages/curl -s http://hermes:8642/v1/responses \
  -H "Authorization: Bearer <API_SERVER_KEY>" -H "Content-Type: application/json" \
  -d '{"model": "default", "input": "สวัสดี", "stream": false}'
```

บน Windows คำสั่ง curl อาจส่งภาษาไทยที่พิมพ์ในบรรทัดคำสั่งผิดเพี้ยนเป็น `?` ให้บันทึก JSON ของคำขอเป็นไฟล์ UTF-8 แล้วส่งด้วย `-d @request.json` แทน

## การปรับให้เหมาะกับงานของคุณ

ค่าต่อไปนี้อยู่ในไฟล์ของเอเจนต์ในโฟลเดอร์ `data/` เมื่อแก้ไขแล้ว ให้สั่ง `docker compose restart gateway`

- **`data/SOUL.md`** บุคลิกและกฎการทำงาน เขียนเป็นภาษาปกติได้เลย เช่น เพิ่มกฎว่าเมื่อผู้ใช้สั่งคำใดให้ใช้เครื่องมือใด
- **`data/skills/`** เพิ่ม skill ของตัวเองเป็นโฟลเดอร์ที่มีไฟล์ `SKILL.md` (ดูตัวอย่างจาก `intelligence-analyzer`) หากต้องการให้ skill ใหม่ถูก commit ด้วย ให้เพิ่มโฟลเดอร์นั้นใน `.gitignore` แบบเดียวกับ `intelligence/`
- **`model` ใน `data/config.yaml`** เปลี่ยน LLM ของเอเจนต์ ควรเลือก model ที่รองรับภาษาไทยและการเรียกใช้เครื่องมือได้ดี
- **`agent.max_turns` ใน `data/config.yaml`** จำนวนรอบเรียกเครื่องมือสูงสุดต่อหนึ่งคำสั่ง เพิ่มได้หากงานวิเคราะห์ยาวถูกตัดกลางคัน
- **`mcp_servers` ใน `data/config.yaml`** เพิ่มหรือถอด MCP server

ส่วนค่าของ docker compose (image, uid/gid, docker network และพอร์ตของ dashboard) ให้กำหนดในไฟล์ `.env` ข้าง `docker-compose.yml` (ดู [`.env.example`](.env.example)) แล้วสั่ง `docker compose up -d`

## ความปลอดภัย

- **API ของเอเจนต์** (พอร์ต 8642) เปิดเฉพาะภายใน docker network และต้องใช้ `API_SERVER_KEY` ทุกครั้ง
  ผู้ที่มี key นี้สั่งเอเจนต์ใช้ทุกเครื่องมือได้ รวมถึง `terminal` ที่รันคำสั่งใน container ของ Hermes โดยตรง จึงต้องเก็บ key เป็นความลับ และให้เฉพาะแอปที่ไว้ใจได้
- **dashboard** (พอร์ต 9119) เปิดให้เครื่องอื่นในเครือข่ายเข้าถึงได้เป็นค่าเริ่มต้น (`DASHBOARD_PUBLISH_ADDR=0.0.0.0`) และต้องเข้าสู่ระบบด้วยรหัสผ่านที่ตั้งไว้ทุกครั้ง หากไม่จำเป็น ให้กำหนด `DASHBOARD_PUBLISH_ADDR=127.0.0.1`
- **ค่าลับทั้งหมด** อยู่ใน `data/.env`, `data/auth.json` และรหัสผ่าน dashboard ใน `data/config.yaml` ซึ่ง `.gitignore` กันไม่ให้ขึ้น git ทั้งโฟลเดอร์ `data/` ยกเว้น SOUL.md และ skill ของเรา
- ควรตั้งวงเงินของ OpenRouter API key ไว้ เพื่อจำกัดค่าใช้จ่ายหากเอเจนต์ทำงานวนนานผิดปกติ

## สำหรับนักพัฒนา

### การอัปเดตเวอร์ชันของ Hermes

ชุดติดตั้งนี้ล็อก image ไว้ที่ `nousresearch/hermes-agent:v0.21.6` หากต้องการอัปเดต ให้กำหนด `HERMES_IMAGE` ในไฟล์ `.env` แล้วสั่ง

```bash
docker compose pull
docker compose up -d
```

จากนั้นตรวจว่า `/health` แสดงเวอร์ชันใหม่ log แสดง `MCP: registered … from 3 server(s)` และโหมดนักวิเคราะห์ยังทำงานได้ ก่อนแก้ค่าเริ่มต้นใน `docker-compose.yml`
Hermes อาจเพิ่มหัวข้อใหม่ใน `data/config.yaml` เองเมื่ออัปเดต จึงควรตรวจว่าค่าที่ตั้งตาม `config.yaml.example` ยังอยู่ครบ

### สิ่งที่ git ติดตาม

`.gitignore` กันทั้งโฟลเดอร์ `data/` เพราะเป็นข้อมูลที่ Hermes สร้างและมีค่าลับ ยกเว้น

- `data/SOUL.md`
- `data/skills/intelligence/`

skill มาตรฐานอื่นใน `data/skills/` เป็นของ Hermes ซึ่งสร้างใหม่เองเมื่อติดตั้ง

## สัญญาอนุญาต

[MIT](LICENSE) © 2026 Chacharin Lertyosbordin
Hermes Agent เป็นลิขสิทธิ์ของ Nous Research ภายใต้สัญญาอนุญาต MIT ([ซอร์สโค้ด](https://github.com/NousResearch/hermes-agent))
