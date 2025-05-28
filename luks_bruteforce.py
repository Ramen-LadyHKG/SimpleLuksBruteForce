import itertools
import subprocess
import tempfile
import os
import argparse

PARTITION = "/dev/sda1"
SYMBOLS = ["", "!", ".", ","]
REPLACEMENTS = {
    'a': ['a', 'A'],
    's': ['s', 'S'],
    'S': ['S', 's'],
    'A': ['A', 'a']
}

TRIED_PASSWORDS_FILE = "tried_passwords.tmp"

def load_keywords(file_path="my_passwords.txt"):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def case_and_replace_variants(word):
    def expand_char(c):
        return REPLACEMENTS.get(c, [c.lower(), c.upper()]) if c.lower() in REPLACEMENTS else [c.lower(), c.upper()]
    return set(
        ''.join(p) for p in itertools.product(*(expand_char(c) for c in word))
    )

def load_tried_passwords():
    if os.path.exists(TRIED_PASSWORDS_FILE):
        with open(TRIED_PASSWORDS_FILE, 'r') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_tried_password(password):
    with open(TRIED_PASSWORDS_FILE, 'a') as f:
        f.write(password + "\n")

def generate_passwords_lazy(keywords, tried_passwords):
    base_variants = set()
    for word in keywords:
        base_variants.update(case_and_replace_variants(word))

    for r in range(1, 4):
        for combo in itertools.permutations(base_variants, r):
            joined = ''.join(combo)
            for symbol in SYMBOLS:
                candidate = joined + symbol
                if candidate not in tried_passwords:
                    yield candidate

def try_passwords(password_gen, debug=False):
    for i, password in enumerate(password_gen, start=1):
        if debug:
            print(f"[{i}] 試緊：{password}")
        else:
            print(f"[{i}] 試緊...", end="\r")

        try:
            with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmpfile:
                tmpfile.write(password)
                tmpfile.flush()
                tmpfile_path = tmpfile.name

            result = subprocess.run(
                ["cryptsetup", "--test-passphrase", "--key-file", tmpfile_path, "open", PARTITION, "my_luks_test"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )

            os.unlink(tmpfile_path)

            if result.returncode == 0:
                print(f"\n[✔] 成功！密碼係：{password}")
                return password
            else:
                save_tried_password(password)

        except subprocess.TimeoutExpired:
            print(f"\n[!] Timeout：密碼 {password} 被跳過")
        except Exception as e:
            print(f"\n[!] 錯誤：{e}")

    print("\n[✘] 所有密碼都唔啱")
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="爆破 LUKS 密碼工具")
    parser.add_argument("--debug", action="store_true", help="開啟詳細 debug 輸出")
    args = parser.parse_args()

    keywords = load_keywords()
    tried_passwords = load_tried_passwords()

    print(f"[INFO] 載入咗 {len(keywords)} 個 keyword：{keywords}")
    print(f"[INFO] 已經試過 {len(tried_passwords)} 條密碼，會略過佢哋")
    print(f"[INFO] 開始爆破...\n")

    password_gen = generate_passwords_lazy(keywords, tried_passwords)
    try_passwords(password_gen, debug=args.debug)
