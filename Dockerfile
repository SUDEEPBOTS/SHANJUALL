# ✅ Naya aur Stable Base Image use kar rahe hain (Node 20 LTS)
# Isse wo 'sed/archive' wali error nahi aayegi
FROM nikolaik/python-nodejs:python3.10-nodejs20

# ✅ System Dependencies (Aria2 aur FFMPEG)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg aria2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/

# ✅ CACHING TRICK: Sirf requirements pehle copy karo
COPY requirements.txt .

# ✅ Install Python packages (Ye ab bar-bar nahi chalega jab tak requirements change na ho)
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir --upgrade -r requirements.txt

# ✅ Ab baaki ka code copy karo
COPY . .

# ✅ Start Command
CMD ["bash", "start"]

