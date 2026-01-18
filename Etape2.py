# pentru fiecare produs:
    # vector_produs = encode(color, size, price)

# pentru fiecare utilizator:
    # produse_cumparate = istoricul_utilizatorului
    # profil_utilizator = media(vector_produs pentru produse_cumparate)

# pentru fiecare utilizator:
    # pentru fiecare produs:
        # scor = cosine_similarity(profil_utilizator, vector_produs)
    # recomandari = top scoruri (excluzând produsele deja cumpărate)
