import argparse, os, logging
from src.TilesToGpkg import TilesToGpkg
from src.utils import gpkg_dump, execute_sql

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Watch a directory for tiles data, and insert to a GeoPackage.")
    parser.add_argument(
        "src_path",
        nargs="?",
        metavar=("SOURCE_PATH"),
        default=os.getcwd(),
        help="Specify the root folder for tiles retrieval. Default is the current working directory.\n"
            "You can provide a custom source path.",
    )
    parser.add_argument(
        "--gpkg_path",
        nargs="?",
        metavar=("PATH"),
        help="Specify the GeoPackage path. Default is './terrain-tiles.gpkg'.\n"
            "You can provide a custom GeoPackage path.",
        default="./terrain-tiles.gpkg",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Use the file watcher. If provided, the script will watch for new and moved files. If omitted, the default behavior is to iterate through the source path searching for tiles.",
    )
    parser.add_argument(
        "--watch_patterns",
        nargs = "+",
        metavar=("FILES_PATTERNS"),
        default=["*.terrain", "layer.json"],
        help="Specify watch patterns if using watcher. Default is ['*.terrain', 'layer.json'].\n"
            "You can provide a list of file patterns to watch.",
    )
    parser.add_argument(
        "--dump",
        nargs="+",
        metavar=("DEST_PATH", "SOURCE_PATH"),
        help="Dumps (append) one GeoPackage db to another. Using ogr2ogr.",
    )
    parser.add_argument(
       '--execute_sql',
       nargs=2,
       metavar=("DB_FILE", "SQL_STATEMENT"),
       help="Execute SQL statements on an SQLite3 db."
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose logging for debugging, may hit performance",
    )

    args = parser.parse_args()

    logLevel = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=logLevel)

    if args.dump:
        if len(args.dump) < 2:
            logger.error("Error: --dump must be followed by DEST_PATH and at least one SOURCE_PATH.")
            exit(1)

        for arg_i in range(len(args.dump) - 1):
            destination = args.dump[0]
            current_source = args.dump[arg_i + 1]
            dump_exit_code = gpkg_dump(destination, current_source)
            if dump_exit_code > 0:
                exit(dump_exit_code)

        logger.info("Successfully merged sources to destination")
        exit(0)
    
    if args.execute_sql:
        exit(execute_sql(args.execute_sql[1], args.execute_sql[0]))

    if not os.path.exists(args.src_path):
        logger.error("Invalid source path. Please specify an existing directory.")
        exit(1)

    if args.watch and not args.watch_patterns:
        logger.error("Please specify watch patterns.")
        exit(1)

    try:
        tiles_to_gpkg = TilesToGpkg(args.src_path, args.gpkg_path, args.watch, [*args.watch_patterns])
    except Exception as e:
        logger.error(f"Error initializing TilesToGpkg: {e}")
        exit(1)

if __name__ == "__main__":
    main()