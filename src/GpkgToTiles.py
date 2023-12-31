import os, logging, threading, time
import concurrent.futures
from src.constants import TERRAIN_TILES_TABLE, LAYER_JSON_TABLE
from src.OGRConnectionPool import OGRConnectionPool

logger = logging.getLogger(__name__)
DEFAULT_WORKERS_NUMBER = 2
class GpkgToTiles:
    def __init__(self, gpkg_path, output_dir, workers = DEFAULT_WORKERS_NUMBER):
        self.gpkg_path = gpkg_path
        self.output_dir = output_dir
        self.workers_count = DEFAULT_WORKERS_NUMBER if workers is None else workers
        self.work_done = threading.Event()

    def extract_terrain_tiles(self, tile_group, gpkg_ds):
        try:
            zoom_level, tile_column = tile_group
            # Construct the directory path based on zoom level and tile column
            tile_dir = os.path.join(self.output_dir, str(zoom_level), str(tile_column))
            os.makedirs(tile_dir, exist_ok=True)
            tiles_data_select = f"SELECT tile_row, tile_data FROM {TERRAIN_TILES_TABLE} WHERE zoom_level={zoom_level} AND tile_column={tile_column}"
            res = gpkg_ds.ExecuteSQL(tiles_data_select)

            for feature in res:
                tile_row = feature.GetField("tile_row")
                tile_data = feature.GetFieldAsBinary("tile_data")
                tile_filename = os.path.join(tile_dir, f"{tile_row}.terrain")
                logger.debug(f"processing {tile_filename}")
                with open(tile_filename, 'wb') as tile_file:
                    tile_file.write(tile_data)
            return True
        except Exception as e:
            logger.error(e)
            return False

    def extract_layer_json(self, connections_pool: OGRConnectionPool):
        gpkg_ds = connections_pool.get_connection()

        try:
            layer = gpkg_ds.GetLayer(LAYER_JSON_TABLE)
            if layer:
                feature = layer.GetFeature((1))
                layer_json_data = feature.GetField("data")
                layer_json_file_name = os.path.join(self.output_dir, "layer.json")

                os.makedirs(self.output_dir, exist_ok=True)

                with open(layer_json_file_name, 'w') as layer_json_file:
                    layer_json_file.write(layer_json_data)         
        except Exception as e:
            logger.warning(f'Problem extracting layer.json from gpkg {e}')
            
        connections_pool.release_connection(gpkg_ds)

    def process_tile_group(self,group, connections_pool):
      gpkg_ds = connections_pool.get_connection()
      try:
          self.extract_terrain_tiles(group, gpkg_ds)
      finally:
          connections_pool.release_connection(gpkg_ds)

    def execute(self):
        connections_pool = OGRConnectionPool(os.cpu_count(), self.gpkg_path)
        startTime = time.time()

        try:
            self.extract_layer_json(connections_pool)
            tile_groups = self.get_tile_groups(connections_pool)
            
            for group in tile_groups:
                self.process_tile_group(group, connections_pool)

            with concurrent.futures.ThreadPoolExecutor(max_workers = self.workers_count) as executor:
                futures = []
                for group in tile_groups:
                    future = executor.submit(self.process_tile_group, group, connections_pool)
                    futures.append(future)

                concurrent.futures.wait(futures, timeout=None)
        except Exception as e:
            logger.error(e)
            exit(1)

        finally:
            endTime = time.time()
            connections_pool.close_all_connections()
            logger.info(f"Extraction Done in {endTime - startTime} Seconds ! Files at {self.output_dir}")

    def get_tile_groups(self, connections_pool: OGRConnectionPool):
      gpkg_ds = connections_pool.get_connection()

      tiles_groups_select = f"SELECT DISTINCT zoom_level, tile_column FROM {TERRAIN_TILES_TABLE}"
      res = gpkg_ds.ExecuteSQL(tiles_groups_select)

      tile_groups = set()
      for feature in res:
          zoom_level = feature.GetField("zoom_level")
          tile_column = feature.GetField("tile_column")
          tile_groups.add((zoom_level, tile_column))
      
      connections_pool.release_connection(gpkg_ds)
      
      return list(tile_groups)