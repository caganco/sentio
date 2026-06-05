# RR-Y1-005 — FAZ-1 RECON DİREKTİFİ (Builder)

**Hedef:** Builder (Claude Code, claude-sonnet-4-x)
**Tip:** RECON — fizibilite-araştırması. **KOD-YOK, BUILD-YOK.** Çıktı = tek yazılı-rapor (markdown).
**Girdi-doküman:** `RR-Y1-005-TEST-MOTORU-TASARIM.md` (önce bunu oku; recon bu tasarımın fizibilitesini ölçer).
**Repo:** github.com/caganco/bist-trading-system

---

## NİYE BU DİREKTİF KOD-İSTEMİYOR
Tasarım kâğıtta donmuş ama varsayımları veriyle/codebase'le henüz-doğrulanmadı. Recon-bulguları spec'i değiştirebilir; spec-kararı Orchestrator+the maintainer'ın (ARCHITECTURE > Builder). Sen önce zemini-haritalayacaksın; build sonraki-faz.

---

## A. CODEBASE ENVANTERİ
1. **Mevcut 5-gate harness:** dosya-konumu, arayüzü, girdi/çıktı-kontratı. Yeni genel-motor bunu *sarmalayabilir* mi (wrap) yoksa *paralel* mi kurulmalı? Hangisi strangler'a-uygun (committed-motor KIRILMAZ)?
2. **cc_cont / C12 artefaktları:** sonuçlar erişilebilir + donmuş-mu? Golden-fixture (§8.1) olarak kullanılabilir-formatta-mı? Değilse ne-gerekir?
3. **realistic_cost (D-207):** mevcut çağrı-arayüzü; yeni-motor onu nasıl-tüketir.
4. **Datahub (3-gün-önce):** panel hangi-formatta (şema, frekans, isim-eksen-zaman-eksen düzeni)? Frekans-dönüşümü (günlük↔aylık) var-mı? Survivorship/delisted-kapsam çağrı-seviyesinde-doğrulanabilir-mi?
5. **Stage-0 ön-kayıt sistemi:** mevcut `docs/yol1/STAGE0_*.json` şeması, yeni §6-şemasını kaldırır-mı yoksa genişletme-mi gerekir?

## B. VERİ-FİZİBİLİTE (tasarım-dial'larını besler)
6. **Embargo-h (§3.4):** mevcut sinyallerde otokorelasyon-sönüm-uzunluğu pratikte-ne (örnek-ölçüm, 1-2 temsili-sinyalde)? Tek-sayı-mı yoksa sinyale-göre-değişken-mi?
7. **İsim-bölmesi fizibilitesi (§3.3):** 2019-2026'da dönem-başına-likit-isim-sayısı kaç? İkiye-bölününce her-yarı istatistiksel-anlamlı-N bırakıyor-mu? Aylık-frekansta durum ne?
8. **Faktör-nötrleme (§3.5):** piyasa-betası / sektör / büyüklük serileri datahub'da-mevcut-mu? Mevcut-değilse hangileri-türetilebilir, hangisi-duvar?
9. **Cut-policy + CPCV (§3.4):** gözlem-sayısı CPCV (N,k) için yeterli-mi? Anlamlı-(N,k) aralığı ne?

## C. BUILDER ALT-TEŞHİS YETKİSİ (the maintainer-speci)
Codebase-içkinlikli sorunlarda **doğrudan alt-teşhis koy ve öneri getir** — burada senin kod-içi görüşün bizimkinden sağlıklı. Örnekler:
- "Mevcut harness X-varsayımını-yapıyor; bu split-modu-A ile çelişiyor; önerim Y."
- "Datahub-arayüzü panel'i Z-formatında-veriyor; isim-bölmesi-için W-adaptörü-gerekir."
- "cc_cont-sonuçları golden-fixture-olamaz çünkü ...; alternatif: ..."

**Sınır:** teşhis/öneri serbest; **mimari/spec-kararını VERME** (onu Orchestrator+the maintainer donar). Sen "şu-sorun-var, şu-seçenekler-var, şunu-öneririm" dersin; "şöyle-yaptım" demezsin.

## D. ÇIKTI FORMATI
Tek markdown-rapor:
1. Her madde (A1-C) için bulgu + kanıt (dosya-yolu/satır/ölçüm).
2. **Açık alt-teşhisler + öneriler** (C-bölümü) ayrı-başlıkta.
3. **Spec-değiştirebilecek bulgular** ayrı-vurgulu (Orchestrator bunlara-bakacak).
4. Fizibilite-hükmü: tasarım-dial'larından hangisi-uygulanabilir / hangisi-veri-duvarlı / hangisi-revize-gerektirir.

**Yapma:** kod-yazma, motor-kurma, test-koşma, mimari-karar-verme, dosya-değiştirme. Sadece-oku, ölç, raporla, öner.
