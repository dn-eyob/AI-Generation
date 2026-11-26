# TTS round-trip results (gemini-3.8-flash-tts -> blind Gemini transcription)

**PARTIAL RESULT:** 9/12 clips completed. Not completed (Gemini free-tier 429 quota / 503 overload, FAILURES F-08): so_s03, so_s07, so_s10.

| Language | Clips | Mean CER | Language ID correct | Chars/s |
|---|---|---|---|---|
| Amharic (am) | 3 | 0.271 | 3/3 | 5.7 |
| Tigrinya (ti) | 3 | 0.356 | 2/3 | 5.8 |
| Afaan Oromo (om) | 3 | 0.227 | 3/3 | 9.2 |
| Somali (so) | 0 | n/a | 0/0 | n/a |

| Lang | Shot | Sent to TTS | Transcribed back | Heard as | CER | Transcriber |
|---|---|---|---|---|---|---|
| am | s03 | የቡናው ጢስ ሲወጣ፣ መጥሪያ ደወል አያስፈልገውም። | የቡናው እስኪወጣ መጥሪያ ደወል ያስፈልጋል። | am | 0.241 | gemini-3.5-flash |
| am | s07 | ቶና ሲደገም፣ የታሪኩ ፈትል ወደ ታናናሾቹ ይሻገራል። | ቶን እና ሲደገም የታሪኩ ፈትል ወደ ታናናሾቹ ይሻገራል። | amh | 0.097 | gemini-3.6-flash |
| am | s10 | በየትኛውም ምድር ብንኖር፣ ይሄ የቤታችን እና የትውስታችን ጠረን ነው። | ቤት አያምድርብን ኖር፤ ይህ የቤታችንና የተወሰነ ጥር ነው። | am | 0.476 | gemini-3.5-flash |
| ti | s03 | ትኪ ቡን ምስ ደየበ፡ ቃል ኣየድልየናን እዩ። | ጥቅቡን ምስ ደየበ ቃል አይድልየኒዩ | ti | 0.346 | gemini-3.6-flash |
| ti | s07 | ምስ ቶና፡ ፈትሊ ተዘክሮ ብህድኣት ናብ ንኣሽቱ ኣእዳው ይሰጋገር። | ምስጦና ፈትል ተዘክሮ በህድኣት ናብ ናእሽቱ አእዳው ይሸጋገር። | ti | 0.205 | gemini-3.6-flash |
| ti | s10 | ኣብ ዓለም ኣብ ዝሃለና ሃሊና፡ ጨና ገዛና እዚ እዩ። | ዓለም አብዛልናም አለና ጭናገዛና እዚህ ነው። | am | 0.516 | gemini-3.6-flash |
| om | s03 | Aarri bunaa yeroo ol ka'u, nu waamuuf jechi hin barbaachisu. | Arrabunna yero olka'uu nuwamu jechiin barbaceesu | om | 0.276 | gemini-3.5-flash-lite |
| om | s07 | Tonaa wajjin, dhumdi yaadannoo suuta gara harka ijoolleetti darba. | Tana wajjiin dumbeeyyaddanoo suuta gara harka ijooleti darbaa. | om | 0.219 | gemini-3.5-flash-lite |
| om | s10 | Addunyaarra eessayyuu yoo jiraanne, urgaan manaa kanuma. | Addunyaarra isayyo jiraanne urgaa maanaa kanuma | om | 0.185 | gemini-3.6-flash |
