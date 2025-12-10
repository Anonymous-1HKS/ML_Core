import google.generativeai as genai

# --- DÁN KEY VÀO GIỮA 2 DẤU NGOẶC KÉP ---
MY_KEY = "AIzaSyAU00TMb_EUlVNWDBKf3yUbSOBDvve-IwM"

print("\n" + "="*30)
print("🔍 ĐANG SOi KEY CỦA BẠN...")
print("="*30)

# 1. Kiểm tra độ dài (Key chuẩn thường dài 39 ký tự)
length = len(MY_KEY)
print(f"📏 Độ dài: {length} ký tự")

if length != 39:
    print(f"⚠️ CẢNH BÁO: Key chuẩn thường là 39 ký tự. Của bạn là {length}.")

# 2. Kiểm tra khoảng trắng thừa
if " " in MY_KEY:
    print("❌ LỖI TO: Có dấu cách (khoảng trắng) trong Key!")
else:
    print("✅ Không có dấu cách thừa.")

# 3. Kiểm tra ký tự đầu/cuối
print(f"👉 Ký tự đầu: '{MY_KEY[0]}'")
print(f"👉 Ký tự cuối: '{MY_KEY[-1]}'")

# 4. Thử kết nối
print("\n📡 Đang thử gửi tín hiệu lên Google...")
genai.configure(api_key=MY_KEY)

try:
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content("Hi")
    print("\n🎉 THÀNH CÔNG! Key hoạt động tốt.")
except Exception as e:
    print("\n💀 VẪN LỖI: ", e)