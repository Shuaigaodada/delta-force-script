from src.main import main


try:
    if __name__ == "__main__":
        main()
except Exception as e:
    print("程序发生未处理的异常:", e)
finally:
    input("按 Enter 键退出...")