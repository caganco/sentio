---
id: DEC-016
title: Critic Backlog System — Persistent Memory for Strategic Findings
date: 2026-05-20
area: Process / Session Management
status: decided
priority: HIGH (process-level)
affects:
  - CRITIC_BACKLOG.md (new, root)
  - CLAUDE.md (boot protocol section)
  - OS_STATE.md (summary block)
  - tests/test_critic_backlog.py (new)
  - docs/DECISIONS.md (index)
rationale: >
  Klasik LLM context decay sorunu: uzun session'larda kritik stratejik
  bulgular yeni promptların ardında kaybolur. 20 May 2026 session'ında
  critic raporunun 6 bulgusu 2 mesajda gözden kaçtı, maintainer
  fark etmedi. Bu, maintainer hatasının ötesinde sistemik bir LLM
  problemidir ve sistematik kalkan gerektirir.
implementation_status: 100% (maintainer tarafından doğrudan yazıldı, arastirma katmani speci gerektirmedi)
test_coverage: >
  tests/test_critic_backlog.py — invariant tests (existence, format,
  audit trail, boot protocol presence)
---

# DEC-016: Critic Backlog System

**Decision Date:** 20 May 2026
**Decided By:** maintainer (maintainer hatasını teşhis sonrası spec)
**Status:** ✅ DECIDED & IMPLEMENTED
**Implementation Owner:** maintainer (doğrudan)

---

## CONTEXT

calisma oturumu (20 May 2026, D-090..D-110) sırasında:

1. **Critic raporu** 6 yapısal alpha-leak bulgusu listeledi (toplam 32-43 puan/yıl tahmini kayıp).
2. **maintainer** sadece bir bulguyu (IC measurement) backlog'a aldı, diğer 5'i pratik olarak unuttu.
3. **maintainer** iki mesaj sonra fark etti: *"Critic raporunda bu kadar önemli şeylerden bahsetmişken neden 2 mesajda hemen unutulmuş gibi davranıldı?"*

Bu, klasik LLM context decay'in operasyonel sonucu. Yeni mesajlar context'in başını "iter", kritik öğeler arka plana düşer.

---

## DECISION

**Persistent memory layer** kuruldu. Üç katmanlı:

### Layer 1 — `CRITIC_BACKLOG.md` (data persistence)

Repo root'unda kalıcı dosya. Format zorunlu:
- ORIGIN (kaynak referansı)
- ACTIVE FINDINGS (CB-XXX numaralı, status alanlı)
- CLOSED FINDINGS (commit hash + doğrulama testi ile kapatılanlar)
- SESSION CHECKPOINT LOG (her session sonu satır eklenir, audit trail)
- DOSYA KURALLARI (silmek/değiştirmek için protokol)

### Layer 2 — `CLAUDE.md` boot protocol (process enforcement)

Her maintainer session başında:
1. CRITIC_BACKLOG.md okunur
2. ACTIVE FINDINGS özetlenir (ilk yanıtta, 1-2 satır)
3. Spec öncesi mental check: "Bu hangi CB-XXX'i kapatıyor?"
4. Session sonu DEVİR bloğunda Critic Backlog durumu güncellenir

### Layer 3 — `tests/test_critic_backlog.py` (mechanical guarantee)

CI'da koşan invariant testleri:
- Dosya silinemez
- Format bozulamaz
- ACTIVE → CLOSED geçişi audit trail bırakmadan olamaz
- CLAUDE.md'den boot protocol kaldırılamaz
- OS_STATE.md'den summary blok kaldırılamaz

Bu üç katman birlikte: **bir maintainer** bilerek/bilmeyerek kuralı bozmaya çalışırsa, **CI kırılır**. Test eğitici hata mesajı verir.

---

## KEY DESIGN DECISIONS

### Neden markdown, neden tool değil?
- Tool gerektirmiyor — her LLM okuyabilir
- Git-tracked — diff görünür, audit kolay
- Insan-okunabilir — maintainer bağımsız olarak inceleyebilir
- Migration riski yok

### Neden arastirma katmani'a vermedik?
- maintainer'un kendi hatasını tespit eden bir kural
- Süreç-seviyesinde, kod değil
- 10 dakikalık iş — formal SPEC + arastirma katmani overhead'i yersizdi
- maintainer doğrudan yazarak kuralı kendisi de pratik etti

### Neden test ekledik?
- "Sadece kural" kuralı korumaz — test mekanik garanti
- Future maintainer silmek isterse CI kırılır
- Test mesajları "neden bu test var" diye açıklar

---

## SESSION-TO-SESSION GUARANTEE

Bu kararın kendisi nesilden nesile devralınır çünkü:

1. **`CRITIC_BACKLOG.md`** dosya olarak repo'da — her yeni session okur
2. **`CLAUDE.md`** boot protocol — her maintainer instance görür
3. **`OS_STATE.md`** summary — session başı snapshot
4. **`test_critic_backlog.py`** — mekanik kapsayıcı, silme girişimini durdurur
5. **`DECISIONS.md`** indeksinde DEC-016 — değişiklik gerekçe gerektirir

Bir gelecek maintainer bu sistemi değiştirmek isterse:
- Yeni DEC yazmalı
- CRITIC_BACKLOG.md SESSION CHECKPOINT LOG'una gerekçeli kayıt
- Eski sistemden ne taşıdığını dokümante etmeli

---

## RELATED DECISIONS

- DEC-015 — Alpha Attribution Faz 1 (IC measurement) — CB-XXX'lerin ölçümlenebilir hale gelmesi için altyapı
- calisma oturumu (20 May 2026) Critic raporu — bu sistemin tetikleyicisi

---

**Status:** ✅ DECIDED & IMPLEMENTED (20 May 2026)
**Implementation files:** CRITIC_BACKLOG.md, CLAUDE.md (boot section), OS_STATE.md (summary block), tests/test_critic_backlog.py
**Approved By:** maintainer
