
import pdal
import json

def list_las_dimensions(las_file_path):
    """
    List all available dimensions in a LAS file using PDAL.
    """
    pipeline_json = {
        "pipeline": [
            las_file_path
        ]
    }
    pipeline = pdal.Pipeline(json.dumps(pipeline_json))
    pipeline.execute()
    metadata = pipeline.metadata
    # The dimensions are under metadata['metadata']['readers.las']['dimensions']
    # The correct way to get dimensions is from the numpy array's dtype names
    arrays = pipeline.arrays
    if not arrays:
        print("No data arrays returned by PDAL pipeline.")
        return
    dims = arrays[0].dtype.names
    print("Available dimensions:")
    for dim in dims:
        print(dim)

# Example usage:
if __name__ == "__main__":
    # Replace this with your actual LAS file path
    las_file = "d:\\Arun\\Enhanced Forest Inventory\\Data\\Airborne\\clipped to plots\\clipped_1.las"
    list_las_dimensions(las_file)
