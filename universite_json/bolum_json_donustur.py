import os
import json
import re
from bs4 import BeautifulSoup

def parse_structured(entry):
    # Program kodu
    kod = entry.get('Program Kodu', '').split('location_on')[0].strip()
    # Üniversite ve fakülte
    uni_fak = entry.get('Üniversite ve Fakülte', '')
    uni_match = re.match(r"([\wÇĞİÖŞÜçğıöşü\s\.\-]+?)(Vakıf|Devlet)(.+)", uni_fak)
    if uni_match:
        uni_adi = uni_match.group(1).strip()
        uni_turu = uni_match.group(2).strip()
        fakulte = uni_match.group(3).strip()
    else:
        uni_adi = uni_fak
        uni_turu = ''
        fakulte = ''
    # Program adı ve detayları
    prog_detay = entry.get('Program Adı ve Detayları', '')
    prog_match = re.match(r"([\wÇĞİÖŞÜçğıöşü\s\.\-]+?)(Önlisans|Lisans|Sözel|Sayısal|Eşit Ağırlık|Uzaktan Öğretim|Açıköğretim|%50 İndirimli|Burslu|Ücretli Uzaktan|KKTC UYRUKLU)?(.*)", prog_detay)
    if prog_match:
        prog_adi = prog_match.group(1).strip()
        ogretim_turu = entry.get('Öğretim Türü', '').strip()
    else:
        prog_adi = prog_detay
        ogretim_turu = entry.get('Öğretim Türü', '').strip()
    # Yıl, kontenjan, yerleşen, taban puan, taban sıralama
    yil_list = re.findall(r'\d{4}', entry.get('Yıl', ''))
    kontenjan_list = re.findall(r'([\d\+\-]+)', entry.get('Kontenjan', ''))
    yerlesen_list = re.findall(r'(Doldu-\d+|\d+[\+\d]*)', entry.get('Yerleşen', ''))
    taban_siralama_list = re.findall(r'(\d{1,3}[\.,]\d{1,3})', entry.get('Taban Sıralama', ''))
    taban_puan_list = re.findall(r'(\d{1,3}[\.,]\d{1,3})', entry.get('Taban Puan', ''))
    # Şehir, ücret
    sehir = entry.get('Şehir', '').strip()
    ucret = entry.get('Ücret', '').strip()
    # Structured entry
    return {
        "Program Kodu": kod,
        "Üniversite": uni_adi,
        "Fakülte": fakulte,
        "Üniversite Türü": uni_turu,
        "Program Adı": prog_adi,
        "Öğretim Türü": ogretim_turu,
        "Yıl": yil_list,
        "Kontenjan": kontenjan_list,
        "Yerleşen": yerlesen_list,
        "Taban Sıralama": taban_siralama_list,
        "Taban Puan": taban_puan_list,
        "Şehir": sehir,
        "Ücret": ucret
    }

def donustur_dosya(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for key in ['yks', 'dgs']:
        if key in data:
            data[key] = [parse_structured(entry) for entry in data[key]]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Dönüştürüldü: {os.path.basename(path)}")

def main():
    dir_path = os.path.dirname(__file__)
    for fname in os.listdir(dir_path):
        if fname.endswith('.json') and fname.startswith('bolum_'):
            donustur_dosya(os.path.join(dir_path, fname))

if __name__ == "__main__":
    main()
