# Error analysis v2: v2_chal / gemini-flash-lite

| Cause | S2 | S2 on gold criteria | Example |
|---|---|---|---|
| Missing English score treated as not met | 7 | 3 | chal002 em-cyberus gold II -> NE |
| Semantic judge too strict (field or motivation) | 8 | 5 | chal010 em-cosi gold II -> NE |
| Both track rules applied | 0 | 4 | chal006 mext-research-guidelines gold E -> NE |
| Short degree below the credit minimum | 0 | 2 | chal035 em-cyberus gold II -> NE |
| Criterion missed or too lenient in extraction | 8 | 3 | chal009 mext-research-guidelines gold II -> E |
| Test threshold not extracted | 5 | 0 | chal042 sh-cs-2720 gold E -> II |
| Only admission or document items (nothing to judge) | 4 | 3 | chal047 sh-cse-ppke gold E -> II |
| Other insufficient-information verdict | 0 | 1 | chal059 em-jemaro gold NE -> II |
| **Total** | **32** | **21** | |
