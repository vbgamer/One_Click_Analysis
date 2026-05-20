import sys

sys.path.append(r"C:\Users\Vedant Bhosale\Desktop\Anal\.venv\Lib\site-packages")

import uvicorn


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
