from app.services.data_refresh import DataRefreshPipeline


def main() -> None:
    DataRefreshPipeline().run()


if __name__ == "__main__":
    main()
