import streamlit as st
import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# KONFIGURASI HALAMAN
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SPK Prioritas Stok – Boutique Jeel",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────
# CSS KUSTOM
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Font Google */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght=400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }

    /* Header utama */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { font-size: 1.8rem; font-weight: 700; margin: 0; }
    .main-header p  { font-size: 0.95rem; opacity: 0.75; margin: 0.25rem 0 0; }

    /* Kartu tahapan */
    .step-card {
        background: #f8faff;
        border: 1px solid #e2e8f7;
        border-left: 4px solid #3a7bd5;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }
    .step-card h4 { color: #1a1a2e; margin: 0 0 0.25rem; font-size: 0.95rem; font-weight: 600; }
    .step-card p  { color: #555; font-size: 0.82rem; margin: 0; }

    /* Metric cards */
    .metric-box {
        background: white;
        border: 1px solid #e2e8f7;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        text-align: center;
    }
    .metric-box .val { font-size: 1.6rem; font-weight: 700; color: #3a7bd5; }
    .metric-box .lbl { font-size: 0.78rem; color: #888; margin-top: 0.2rem; }

    /* Rekomendasi box */
    .rekomendasi {
        background: linear-gradient(135deg, #0f3460, #3a7bd5);
        color: white;
        border-radius: 14px;
        padding: 1.5rem 2rem;
        margin-top: 1rem;
    }
    .rekomendasi h3 { margin: 0 0 0.4rem; font-size: 1.1rem; }
    .rekomendasi p  { margin: 0; font-size: 0.9rem; opacity: 0.9; }

    /* Sticky formula */
    .formula-box {
        background: #1e293b;
        color: #e2e8f7;
        font-family: monospace;
        font-size: 0.82rem;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        line-height: 1.8;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1> SPK Prioritas Stok – Boutique Jeel</h1>
    <p>Sistem Penunjang Keputusan berbasis metode TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("Konfigurasi Model")
    uploaded_file = st.file_uploader("Upload File CSV Penjualan", type=["csv"])

    if uploaded_file:
        st.divider()
        st.subheader("1. Filter Kelayakan")
        min_qty = st.number_input(
            "Minimal Terjual (Pcs)", min_value=1, value=10,
            help="Produk dengan total penjualan di bawah angka ini tidak akan diproses."
        )

        st.divider()
        st.subheader("2. Bobot Kriteria")
        st.info("**1** = Rendah  ·  **2** = Sedang  ·  **3** = Tinggi\n\nBobot akan dinormalisasi otomatis sehingga totalnya = 1.")
        w_rev = st.slider("C1 – Revenue (Keuntungan)",       1, 3, 2)
        w_qty = st.slider("C2 – Qty Terjual (Volume)",       1, 3, 2)
        w_ret = st.slider("C3 – Rasio Retur (Risiko)",       1, 3, 1)

        # Label bobot
        w_total = w_rev + w_qty + w_ret
        bobot_label = {1: "🔵 Rendah", 2: "🟡 Sedang", 3: "🔴 Tinggi"}
        st.markdown(f"""
        <div style="background:#f0f4ff; border-radius:8px; padding:0.6rem 1rem; font-size:0.82rem; color:#444; margin-bottom:0.5rem;">
        &nbsp;&nbsp;C1 → <b>{bobot_label[w_rev]}</b> &nbsp;|&nbsp;
        C2 → <b>{bobot_label[w_qty]}</b> &nbsp;|&nbsp;
        C3 → <b>{bobot_label[w_ret]}</b>
        </div>
        """, unsafe_allow_html=True)

        wn_rev = w_rev / w_total
        wn_qty = w_qty / w_total
        wn_ret = w_ret / w_total

        st.markdown(f"""
        <div class="formula-box">
        W_norm = [{wn_rev:.3f}, {wn_qty:.3f}, {wn_ret:.3f}]<br>
        (total = {wn_rev+wn_qty+wn_ret:.3f})
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.caption("Kriteria C1 & C2 = **Benefit** (makin besar makin baik)")
        st.caption("Kriteria C3 = **Cost** (makin kecil makin baik)")


# ─────────────────────────────────────────────
# FUNGSI TOPSIS (BENAR SECARA AKADEMIS)
# ─────────────────────────────────────────────
def topsis(df_raw, w_rev, w_qty, w_ret, min_qty):
    # ── Cleaning ──────────────────────────────
    df = df_raw.drop(index=0).reset_index(drop=True)

    def clean_num(col):
        return pd.to_numeric(
            df[col].astype(str).str.replace(',', '', regex=False),
            errors='coerce'
        ).fillna(0)

    df['Qty_Clean'] = clean_num('Quantity')
    df['Rev_Clean'] = clean_num('SKU Subtotal After Discount')
    df['Ret_Clean'] = clean_num('Sku Quantity of return')

    # ── Agregasi per produk ───────────────────
    agg = df.groupby('Product Name').agg(
        Qty=('Qty_Clean', 'sum'),
        Rev=('Rev_Clean', 'sum'),
        Ret=('Ret_Clean', 'sum')
    ).reset_index()

    # ── Filter minimal terjual ────────────────
    agg = agg[agg['Qty'] >= min_qty].copy().reset_index(drop=True)
    if agg.empty:
        return None, None, None, None, None, None, None

    # ── Fitur turunan ─────────────────────────
    agg['Harga_Rata'] = (agg['Rev'] / agg['Qty']).round(0)
    agg['Rasio_Retur'] = (agg['Ret'] / agg['Qty']).round(4)

    # ══════════════════════════════════════════
    # LANGKAH 1 – MATRIKS KEPUTUSAN (X)
    # ══════════════════════════════════════════
    X = agg[['Rev', 'Qty', 'Rasio_Retur']].values.astype(float)
    labels_produk = agg['Product Name'].tolist()
    labels_krit   = ['C1 (Revenue)', 'C2 (Qty Terjual)', 'C3 (Rasio Retur)']

    # ══════════════════════════════════════════
    # LANGKAH 2 – NORMALISASI VEKTOR EUCLIDEAN
    # ══════════════════════════════════════════
    norm_factor = np.sqrt((X ** 2).sum(axis=0))   # shape (3,)
    R = X / (norm_factor + 1e-12)                 # shape (n, 3)

    # ══════════════════════════════════════════
    # LANGKAH 3 – MATRIKS TERNORMALISASI TERBOBOT
    # ══════════════════════════════════════════
    w_total = w_rev + w_qty + w_ret
    weights = np.array([w_rev / w_total, w_qty / w_total, w_ret / w_total])
    V = R * weights   # shape (n, 3)

    # ══════════════════════════════════════════
    # LANGKAH 4 – SOLUSI IDEAL
    # ══════════════════════════════════════════
    A_pos = np.array([V[:, 0].max(), V[:, 1].max(), V[:, 2].min()])  # A+
    A_neg = np.array([V[:, 0].min(), V[:, 1].min(), V[:, 2].max()])  # A-

    # ══════════════════════════════════════════
    # LANGKAH 5 – JARAK EUCLIDEAN
    # ══════════════════════════════════════════
    D_pos = np.sqrt(((V - A_pos) ** 2).sum(axis=1))
    D_neg = np.sqrt(((V - A_neg) ** 2).sum(axis=1))

    # ══════════════════════════════════════════
    # LANGKAH 6 – NILAI PREFERENSI
    # ══════════════════════════════════════════
    CC = D_neg / (D_pos + D_neg + 1e-12)
    agg['Skor_TOPSIS'] = (CC * 100).round(4)
    agg['D_pos']       = D_pos.round(6)
    agg['D_neg']       = D_neg.round(6)
    agg = agg.sort_values('Skor_TOPSIS', ascending=False).reset_index(drop=True)
    agg['Rank'] = range(1, len(agg) + 1)

    # ── Susun DataFrame tiap tahap ────────────
    df_X = pd.DataFrame(X, columns=labels_krit, index=labels_produk)
    df_X.index.name = 'Produk'

    df_R = pd.DataFrame(R.round(6), columns=labels_krit, index=labels_produk)
    df_R.index.name = 'Produk'

    df_V = pd.DataFrame(V.round(6), columns=labels_krit, index=labels_produk)
    df_V.index.name = 'Produk'

    df_ideal = pd.DataFrame(
        [A_pos, A_neg],
        columns=labels_krit,
        index=['A+ (Ideal Positif)', 'A- (Ideal Negatif)']
    ).round(6)
    df_ideal.index.name = 'Solusi'

    return agg, df_X, df_R, df_V, df_ideal, D_pos, D_neg


# ─────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────
if uploaded_file is not None:
    df_input = pd.read_csv(uploaded_file)
    hasil, df_X, df_R, df_V, df_ideal, D_pos, D_neg = topsis(
        df_input, w_rev, w_qty, w_ret, min_qty
    )

    if hasil is None:
        st.warning("Data kosong setelah filter. Coba turunkan nilai 'Minimal Terjual'.")
    else:
        total_produk = len(hasil)
        best = hasil.iloc[0]
        worst = hasil.iloc[-1]

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="metric-box"><div class="val">{total_produk}</div><div class="lbl">Total Produk Dianalisis</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="metric-box"><div class="val">{best['Skor_TOPSIS']:.2f}</div><div class="lbl">Skor Tertinggi</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-box"><div class="val">{worst['Skor_TOPSIS']:.2f}</div><div class="lbl">Skor Terendah</div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="metric-box"><div class="val">{hasil['Rasio_Retur'].mean()*100:.1f}%</div><div class="lbl">Rata-rata Rasio Retur</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ─────────────────────────────────────
        # TAB NAVIGASI
        # ─────────────────────────────────────
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Hasil Akhir",
            "Langkah 1 – Matriks Keputusan",
            "Langkah 2 – Normalisasi",
            "Langkah 3 – Matriks Terbobot",
            "Langkah 4–5 – Ideal & Jarak",
            "Langkah 6 – Skor & Peringkat",
        ])

        with tab1:
            col_tbl, col_chart = st.columns([3, 2])

            with col_tbl:
                st.subheader("Tabel Peringkat Produk")
                tampil = hasil[[
                    'Rank', 'Product Name', 'Harga_Rata', 'Rev',
                    'Qty', 'Ret', 'Rasio_Retur', 'D_pos', 'D_neg', 'Skor_TOPSIS'
                ]].copy()
                tampil.columns = [
                    'Rank', 'Nama Produk', 'Harga Rata-rata', 'Revenue (Rp)',
                    'Qty Terjual', 'Jml Retur', 'Rasio Retur', 'D+ (Jarak Positif)',
                    'D− (Jarak Negatif)', 'Skor TOPSIS'
                ]
                tampil['Harga Rata-rata'] = tampil['Harga Rata-rata'].apply(lambda x: f"Rp {x:,.0f}")
                tampil['Revenue (Rp)']    = tampil['Revenue (Rp)'].apply(lambda x: f"Rp {x:,.0f}")
                tampil['Rasio Retur']     = tampil['Rasio Retur'].apply(lambda x: f"{x*100:.2f}%")

                st.dataframe(tampil, use_container_width=True, hide_index=True)

            with col_chart:
                st.subheader("Top 10 Skor TOPSIS")
                chart_data = hasil.head(10).set_index('Product Name')['Skor_TOPSIS']
                st.bar_chart(chart_data)

            st.markdown(f"""
            <div class="rekomendasi">
                <h3>Rekomendasi Utama</h3>
                <p>Berdasarkan analisis TOPSIS dengan {total_produk} produk dan bobot yang ditetapkan,
                produk dengan prioritas stok tertinggi adalah <strong>{best['Product Name']}</strong>
                dengan skor TOPSIS <strong>{best['Skor_TOPSIS']:.4f} / 100</strong>.<br>
                Produk ini unggul dalam kombinasi revenue, volume penjualan, dan rasio retur
                dibandingkan produk lainnya.</p>
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 1 – Matriks Keputusan (X)</h4>
                <p>Matriks awal berisi nilai mentah setiap alternatif (produk) pada setiap kriteria.
                Terdiri dari 3 kriteria: <b>C1 = Revenue</b>, <b>C2 = Qty Terjual</b>, <b>C3 = Rasio Retur</b>.</p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(
                df_X.style.format("{:,.4f}").background_gradient(cmap='Blues', axis=0),
                use_container_width=True
            )

        with tab3:
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 2 – Normalisasi Matriks Keputusan (R)</h4>
                <p>Setiap nilai dinormalisasi menggunakan pembagi berupa akar jumlah kuadrat tiap kolom
                (normalisasi vektor Euclidean) sehingga skala antar kriteria menjadi setara.</p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(
                df_R.style.format("{:.6f}").background_gradient(cmap='Greens', axis=0),
                use_container_width=True
            )

        with tab4:
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 3 – Matriks Ternormalisasi Terbobot (V)</h4>
                <p>Setiap nilai ternormalisasi dikalikan dengan bobot kriteria yang telah dinormalisasi.</p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(
                df_V.style.format("{:.6f}").background_gradient(cmap='Oranges', axis=0),
                use_container_width=True
            )

        with tab5:
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 4 – Solusi Ideal Positif (A⁺) & Negatif (A⁻)</h4>
                <p>A⁺ = solusi terbaik yang diharapkan. A⁻ = solusi terburuk. Ditentukan per jenis kriteria.</p>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(
                df_ideal.style.format("{:.6f}").highlight_max(color='#d4edda').highlight_min(color='#f8d7da'),
                use_container_width=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 5 – Jarak Euclidean ke Solusi Ideal</h4>
                <p>D⁺ = jarak setiap produk ke solusi ideal positif. D⁻ = jarak ke solusi ideal negatif.</p>
            </div>
            """, unsafe_allow_html=True)

            df_jarak = pd.DataFrame({
                'Produk': hasil.sort_values('Rank')['Product Name'].values,
                'D+ (Jarak ke Ideal Positif)': hasil.sort_values('Rank')['D_pos'].values,
                'D− (Jarak ke Ideal Negatif)': hasil.sort_values('Rank')['D_neg'].values,
            })
            st.dataframe(
                df_jarak.style.format({'D+ (Jarak ke Ideal Positif)': '{:.6f}', 'D− (Jarak ke Ideal Negatif)': '{:.6f}'})
                              .background_gradient(subset=['D+ (Jarak ke Ideal Positif)'], cmap='Reds')
                              .background_gradient(subset=['D− (Jarak ke Ideal Negatif)'], cmap='Greens'),
                use_container_width=True,
                hide_index=True
            )

        with tab6:
            st.markdown("""
            <div class="step-card">
                <h4>Langkah 6 – Nilai Preferensi / Skor TOPSIS (CC)</h4>
                <p>Semakin tinggi nilai CC (mendekati 1 / skor 100), prioritas stok lebih tinggi.</p>
            </div>
            """, unsafe_allow_html=True)

            df_skor = hasil[['Rank', 'Product Name', 'D_pos', 'D_neg', 'Skor_TOPSIS']].copy()
            df_skor.columns = ['Rank', 'Nama Produk', 'D+', 'D−', 'Skor TOPSIS (CC × 100)']

            st.dataframe(
                df_skor.style.format({'D+': '{:.6f}', 'D−': '{:.6f}', 'Skor TOPSIS (CC × 100)': '{:.4f}'})
                             .background_gradient(subset=['Skor TOPSIS (CC × 100)'], cmap='YlGn'),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Podium Top 3")
            top3 = hasil.head(3)
            medals = ["🥇", "🥈", "🥉"]
            col_a, col_b, col_c = st.columns(3)
            for i, (col, medal) in enumerate(zip([col_a, col_b, col_c], medals)):
                if i < len(top3):
                    row = top3.iloc[i]
                    with col:
                        st.markdown(f"""
                        <div class="metric-box" style="border-top: 4px solid #3a7bd5;">
                            <div style="font-size:2rem">{medal}</div>
                            <div style="font-weight:700; font-size:0.9rem; margin:0.5rem 0;">{row['Product Name']}</div>
                            <div class="val">{row['Skor_TOPSIS']:.2f}</div>
                            <div class="lbl">Skor TOPSIS</div>
                        </div>
                        """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 2rem; color: #aaa;">
        <div style="font-size: 4rem;">📂</div>
        <h3 style="color: #555; margin-top: 1rem;">Upload file CSV penjualan untuk memulai analisis</h3>
        <p>Pastikan CSV memiliki kolom: <code>Product Name</code>, <code>Quantity</code>,
        <code>SKU Subtotal After Discount</code>, <code>Sku Quantity of return</code></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Alur Perhitungan TOPSIS")

    steps = [
        ("Langkah 1", "Matriks Keputusan (X)", "Susun data mentah produk: Revenue, Qty Terjual, dan Rasio Retur."),
        ("Langkah 2", "Normalisasi Vektor Euclidean (R)", "r_ij = x_ij / √(Σ x_ij²) — menyamakan skala antar kriteria."),
        ("Langkah 3", "Matriks Ternormalisasi Terbobot (V)", "v_ij = w_j × r_ij — bobot dinormalisasi agar totalnya = 1."),
        ("Langkah 4", "Solusi Ideal Positif (A⁺) & Negatif (A⁻)", "A⁺ = max benefit & min cost. A⁻ = min benefit & max cost."),
        ("Langkah 5", "Jarak Euclidean (D⁺ & D⁻)", "D⁺ = jarak ke A⁺, D⁻ = jarak ke A⁻."),
        ("Langkah 6", "Nilai Preferensi / Skor TOPSIS", "CC_i = D⁻_i / (D⁺_i + D⁻_i). Urutkan descending."),
    ]

    c1, c2 = st.columns(2)
    for i, (no, judul, desc) in enumerate(steps):
        col = c1 if i % 2 == 0 else c2
        with col:
            st.markdown(f"""
            <div class="step-card">
                <h4>{no} – {judul}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)