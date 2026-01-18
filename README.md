# Sistem de Recomandare pentru Haine (Clothing Recommendation System)

## 1. FUNCȚIONALITATE SISTEM DE RECOMANDARE 

### Tip de Sistem: **CONTENT-BASED HYBRID**

#### Descriere Funcționare:

Sistemul de recomandare utilizează o abordare **content-based cu elemente hibride**:

1. **Content-Based Component:**
   - Analiza caracteristicilor produselor: culoare, mărime, preț
   - Encoding one-hot pentru culori și mărimi
   - Normalizare min-max pentru preț (0-1)
   - Calculul similarității cosine între profilul utilizatorului și produse

2. **Hybrid Component:**
   - Profilul utilizatorului = media vectorilor produselor cumpărate
   - Integrare cu Recombee pentru colectarea interacțiunilor
   - Timestamp-uri pentru temporalitate (recent purchases weighted)

3. **Algoritm Principal (din Etape2.py):**
```python
Pentru fiecare utilizator:
  1. Extrage istoricul de cumpărături
  2. Calculează vectorul de caracteristici pentru fiecare produs cumpărat
  3. Creează profil utilizator = media(vectori_produse)
  4. Pentru fiecare produs din catalog (exceptând cumpărăturile anterioare):
     - Calcul scor = cosine_similarity(profil_utilizator, vector_produs)
  5. Returnează Top-N produse cu scoruri maxime
```

4. **Metrici Utilizate:**
   - Similaritate Cosine (0-1): Măsoară similitudinea dintre profilul utilizatorului și produse
   - Segment Preț (low/mid/premium): Contextualiza preferințele utilizatorului
   
#### De Ce Content-Based?
- Nu necesită date masive de interacțiuni pentru a recomanda
- Lucrul bun pentru produse noi (fără istoric)
- Explicabil utilizatorilor (recomandare pe baza caracteristicilor produselor)
- Control asupra caracteristicilor urmărite

---

## 2. MODELUL UTILIZATORULUI

### Date Colectate și Stocate în Recombee:

#### A. Profilul Utilizatorului (User Properties):
```json
{
  "user_id": "1-273",
  "total_spending": "sum(revenue_purchases)",
  "purchase_count": "count(purchases)",
  "preferred_price_segment": "low|mid|premium"
}
```

#### B. Istoricul Cumpărăturilor (Interactions):
```json
{
  "user_id": "1",
  "item_id": "708",
  "interaction_type": "purchase",
  "timestamp": "2022-06-01 16:05:00"
}
```

#### C. Date din CSV (women_clothing_ecommerce_sales.csv):
- `order_id`: ID unic al comenzii / utilizator
- `order_date`: Data și ora achiziției
- `sku`: ID produs
- `color`: Culoarea hainei (Dark Blue, Cream, Black, etc.)
- `size`: Mărimea (XL, 2XL, One Size, M, etc.)
- `unit_price`: Preț unitar ($228-$298)
- `quantity`: Cantitate cumpărată
- `revenue`: Venit pe tranzacție

#### D. Segmentarea Utilizatorilor (din demo.py):
```python
q1, q2 = preț.quantile([0.33, 0.66])
Segment LOW:     preț <= q1
Segment MID:     q1 < preț <= q2
Segment PREMIUM: preț > q2
```

### Statistici Dataset:
- **273 utilizatori unici** (order_ids 1-273)
- **20 produse unice** (SKU: 708, 89, bobo, 799, 897, 9699, 127, 1719, 3799, 229, 2499, 79, 29, 1499, 628, 61399, 218, 8499, 3081, 539)
- **529 tranzacții totale**
- **Culori**: Dark Blue, Navy Blue, Blue, Light Gray, Cream, Black
- **Mărimi**: XL, 2XL, 3XL, M, One Size, (empty/missing)

---

## 3. FLOW-URI COMPLETE 

### EXEMPLUL 1: USER_A (Cumpărător Regular cu Preferințe Stabile)

**Date Inițiale (din demo.py):**
```
user_A:
  - 2026-01-10: Cumpără SKU 799 (Dark Blue, XL, $264)
  - 2026-01-12: Cumpără SKU 708 (Dark Blue, XL, $278)
  Total Spent: $542
```

**Step 1: Extrag Caracteristici Produse**
```
SKU 799:  [0,1,0,...,0.88] (Dark Blue encoded, XL encoded, normalized_price=0.88)
SKU 708:  [0,1,0,...,0.93] (Dark Blue encoded, XL encoded, normalized_price=0.93)
```

**Step 2: Calcul Profil Utilizator**
```
Profil_A = Media([799_vector, 708_vector])
         = [0, 1, 0, ..., 0.905]  (preferință pentru Dark Blue + XL + preț premium)
```

**Step 3: Evaluare Alte Produse**
```
Similarity(Profil_A, SKU_bobo)  = 0.45  (Cream color ≠ Dark Blue)
Similarity(Profil_A, SKU_89)    = 0.92  (Dark Blue ✓, 2XL similar XL ✓, preț similar ✓)
Similarity(Profil_A, SKU_229)   = 0.38  (Black ≠ Dark Blue)
```

**Step 4: Recomandări (Top-3 ExcluzândDeja Cumpărate)**
```
1. SKU 89   - Similarity: 0.92  ← RECOMANDARE 1
2. SKU 1719 - Similarity: 0.85  ← RECOMANDARE 2
3. SKU 3799 - Similarity: 0.78  ← RECOMANDARE 3
```

**Justificare:** User_A cumpără doar Dark Blue în mărimi mari (XL+) la prețuri premium. Recomandările urmăresc exact acest pattern.

---

### EXEMPLUL 2: USER_B (Cumpărător cu Schimbare de Preferințe - Session Shift)

**Date Inițiale (din demo.py):**
```
user_B:
  - 2026-01-08: Cumpără SKU 897  (preț standard)
  - 2026-01-09: Cumpără SKU 127  (preț standard)
  - 2026-01-18: VIZUALIZEAZĂ SKU 500 (fără cumpărare) ← Schimbare sesiune!
  Total Spent: $582
```

**Step 1: Caracteristici Inițiale**
```
SKU 897:  Vector cu caracteristici X
SKU 127:  Vector cu caracteristici Y
Media(X, Y) = Profil initial
```

**Step 2: Vizualizare Produs Diferit**
```
Moment: 2026-01-18 (după 9 zile)
User_B vizualizează SKU 500 (diferit de pattern anterior)
→ Semnalizează potențiala schimbare de preferințe
```

**Step 3: Recomandări Adaptive**
```
Opțiune 1 (Content-based pur): Recomandă pe bază vectori medii
  → SKU care sunt similare cu 897 și 127

Opțiune 2 (Temporal/Hybrid): Consideră vizualizarea recentă
  → SKU similare cu 500 (preferință nouă)
  → SKU similare cu mediile vechi (inerție preferințe)
```

**Recomandări Rezultate:**
```
1. SKU similare cu mediile 897+127  (85% greutate)
2. SKU similare cu 500              (15% greutate - schimbare recentă)
```

**Justificare:** User_B demonstrează schimbare de sesiune (session shift). Sistemul trebuie să balanseze preferințele vechi cu noile semnale.

---

### EXEMPLUL 3: USER_C (Cumpărător Versatil - Preferințe Diverse)

**Date Concrete din Dataset:**
```
user_15:
  - Order 1: SKU bobo (Cream, One Size, $228)
  - Order 2: SKU bobo (Navy Blue, One Size, $228)
  - Order 3: SKU bobo (Blue, One Size, $228)
  - Order 4: SKU bobo (Light Gray, One Size, $228)
  Total Spent: $912 (4 cumpărături diferite, doar culori diferite)
```

**Step 1: Analiza Pattern-ului**
```
Observație: User_15 cumpără ACELAȘI produs (bobo) dar în CULORI DIFERITE
→ Preferință: PRODUCT LOYALTY cu Color VARIETY
→ Profil = Medie vectori cu aceeași mărime/preț dar culori diverse
```

**Step 2: Vectori Caracteristici**
```
SKU bobo (Cream):      [1,0,0,0,1,0,...,0.76] (One Size, $228 - preț low)
SKU bobo (Navy Blue):  [0,1,0,0,1,0,...,0.76]
SKU bobo (Blue):       [0,0,1,0,1,0,...,0.76]
SKU bobo (Light Gray): [0,0,0,1,1,0,...,0.76]

Profil_15 = [0.25, 0.25, 0.25, 0.25, 1, 0, ..., 0.76]
→ Preferință UNIFORMĂ pentru culori, ONE SIZE, low-mid preț
```

**Step 3: Evaluare Alte Produse**
```
SKU cu One Size + preț similar → Similaritate ÎNALTĂ
SKU cu mărimi diferite (XL, M) → Similaritate SCĂZUTĂ
SKU cu preț mult mai mare     → Similaritate SCĂZUTĂ
```

**Step 4: Recomandări (Top-5)**
```
1. SKU 2499 (One Size, $228) - Similarity: 0.94 ← RECOMANDARE 1
2. SKU 229  (One Size, $258) - Similarity: 0.88 ← RECOMANDARE 2
3. SKU 89   (Diverse culori disponibile) - Similarity: 0.65 ← RECOMANDARE 3
4. Alte SKU ONE SIZE - similaritate în scădere
5. SKU cu mărimi fixe (XL/M) - similaritate foarte scăzută
```

**Justificare:** User_15 are preferințe FOARTE SPECIFICE:
- ✓ Aceiași produs în culori multiple
- ✓ STRICT One Size
- ✓ Preț low-mid ($228-$258)

Sistemul recomandă doar produse care se potrivesc EXACT acestui profil.

---

## 4. INTEGRARE RECOMBEE

### Fluxul Complet (recombee.py):

```
1. DEFINIRE PROPRIETĂȚI
   ├─ Item Properties: color, size, unit_price, order_date, quantity, revenue
   └─ User Properties: total_spending

2. ADĂUGARE ENTITĂȚI
   ├─ Items: 20 produse unice
   ├─ Users: 273 utilizatori unici
   └─ Properties: 6 item properties + 1 user property

3. SETARE VALORI PROPRIETĂȚI
   ├─ SetItemValues: 489 rânduri din CSV (some items missing)
   └─ SetUserValues: 273 utilizatori cu total_spending calculat

4. ADĂUGARE INTERACȚIUNI
   └─ AddPurchase: 489 interacțiuni (user + item + timestamp)
```

### Rezultate Așteptate în Recombee Dashboard:
```
Items Tab:
  ✓ 20 produse cu proprietăți complete
  ✓ Fiecare item: color, size, unit_price, order_date, quantity, revenue

Users Tab:
  ✓ 273 utilizatori cu total_spending calculat
  ✓ Exemple: user_1 ($754), user_15 ($912), user_73 ($1473)

Interactions Tab:
  ✓ 489 purchase events cu timestamp-uri
  ✓ Linkuri user → item
```

---

## 5. TESTARE ȘI VALIDARE

### Cum să Rulezi Sistemul:

```bash
# 1. Sincronizare date cu Recombee
python recombee.py

# 2. Rulare demo cu flow-uri
python demo.py

# 3. Rulare algoritm SR
python Etape2.py
```

### Ce Se Întâmplă în Fiecare:

**sync_to_recombee.py**: Upload complet al datelor
- Properties, Items, Users, Interactions

**demo.py**: Exemple de flow-uri
- Simulează user_A, user_B, user_B (session shift)
- Interacțiuni cu timestamp-uri

**Etape2.py**: Algoritm SR content-based
- Encoding produse
- Calculul similarității
- Recomandări bazate pe profil utilizator