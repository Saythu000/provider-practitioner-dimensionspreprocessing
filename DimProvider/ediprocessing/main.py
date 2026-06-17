import os
import sys
import shutil
from pathlib import Path

# Setup workspace environment paths
file_dir = Path(os.getcwd())
root_dir = file_dir.parent.parent
print("root directory: ", root_dir)

sys.path.append(str(root_dir))

from shared.EDIProcessing.ediprocessing import EDIProcessor
from shared.EDIProcessing.csvconverter import CSVConverter
from DimProvider.ediprocessing.mapper import CSVSchemaMapper


def process_file(source_dir: Path, pending_file: Path, output_file: Path, process_fn):
    """
    Generic file state machine:
      pending -> inprogress -> processed (success)
                            -> failed    (error)

    Args:
        source_dir:   Root source directory (e.g. source/837)
        pending_file: Full path to the file in pending/
        output_file:  Full path where the output CSV will be written
        process_fn:   Callable that takes (active_file_path: str) and returns mapped data list
    """
    inprogress_dir = source_dir / "inprogress"
    processed_dir  = source_dir / "processed"
    failed_dir     = source_dir / "failed"

    active_file = pending_file

    try:
        # 1. Verification Step
        if not active_file.exists():
            raise FileNotFoundError(f"Input file not found in pending: {active_file}")

        # 2. Transition: Pending -> Inprogress
        os.makedirs(inprogress_dir, exist_ok=True)
        inprogress_file = inprogress_dir / active_file.name
        print(f"Moving file to execution phase: {inprogress_file}")
        shutil.move(str(active_file), str(inprogress_file))
        active_file = inprogress_file

        # 3. Sequential Ingestion Pipeline Execution
        structured_json = EDIProcessor().parse(str(active_file))
        mapped_data     = process_fn(structured_json)

        # 4. Destination Directory Creation & Delivery (CSV)
        os.makedirs(output_file.parent, exist_ok=True)
        CSVConverter(schemas_dir=str(root_dir / "DimProvider/bronze/schema")).convert_to_csv(
            mapped_data=mapped_data,
            schema_filename=output_file.stem.replace("1", "").replace("provider_hierarchy", "provider_hierarchy_7.12_schema").replace("provider", "provider_7.12_schema") + ".json",
            output_csv_path=str(output_file)
        )
        print(f"Pipeline execution completed successfully! Output: {output_file}")

        # 5. Transition: Inprogress -> Processed
        os.makedirs(processed_dir, exist_ok=True)
        processed_file = processed_dir / active_file.name
        print(f"Moving file to completion phase: {processed_file}")
        shutil.move(str(active_file), str(processed_file))

    except Exception as e:
        print(f"Execution failed due to: {e}")

        # 6. Transition: Inprogress -> Failed
        if active_file.exists():
            os.makedirs(failed_dir, exist_ok=True)
            failed_file_path = failed_dir / active_file.name
            print(f"Moving file to failure directory: {failed_file_path}")
            shutil.move(str(active_file), str(failed_file_path))
        else:
            print(f"Cannot move file to failed - it does not exist at: {active_file}")

        raise e


def main():
    mapper = CSVSchemaMapper()
    schemas_dir = str(root_dir / "DimProvider/bronze/schema")

    # ----------------------------------------------------------------
    # Pipeline 1: Claims (EDI 837) -> provider.csv
    # ----------------------------------------------------------------
    source_837   = root_dir / "source/837"
    pending_837  = source_837 / "pending/provider1.txt"
    output_837   = root_dir / "temp/837/provider1.csv"

    print("\n=== Processing Claims (EDI 837) ===")
    try:
        if not pending_837.exists():
            print(f"No pending 837 file found at: {pending_837}. Skipping.")
        else:
            inprogress_dir = source_837 / "inprogress"
            processed_dir  = source_837 / "processed"
            failed_dir     = source_837 / "failed"
            active_file    = pending_837

            # Transition: Pending -> Inprogress
            os.makedirs(inprogress_dir, exist_ok=True)
            inprogress_file = inprogress_dir / active_file.name
            print(f"Moving file to execution phase: {inprogress_file}")
            shutil.move(str(active_file), str(inprogress_file))
            active_file = inprogress_file

            # Parse -> Map -> Convert
            structured_json   = EDIProcessor().parse(str(active_file))
            provider_profiles = mapper.map_provider(structured_json)
            os.makedirs(output_837.parent, exist_ok=True)
            CSVConverter(schemas_dir=schemas_dir).convert_providers(
                mapped_providers=provider_profiles,
                output_csv_path=str(output_837)
            )
            print(f"Claims processing complete. Output: {output_837}")

            # Transition: Inprogress -> Processed
            os.makedirs(processed_dir, exist_ok=True)
            processed_file = processed_dir / active_file.name
            shutil.move(str(active_file), str(processed_file))
            print(f"Moving file to completion phase: {processed_file}")

    except Exception as e:
        print(f"Claims (837) pipeline failed: {e}")
        raise e

    # ----------------------------------------------------------------
    # Pipeline 2: Directory (EDI 274) -> provider_hierarchy.csv
    # ----------------------------------------------------------------
    source_274  = root_dir / "source/274"
    pending_274 = source_274 / "pending/provider_hierarchy1.txt"
    output_274  = root_dir / "temp/274/provider_hierarchy1.csv"

    print("\n=== Processing Directory (EDI 274) ===")
    try:
        if not pending_274.exists():
            print(f"No pending 274 file found at: {pending_274}. Skipping.")
        else:
            inprogress_dir = source_274 / "inprogress"
            processed_dir  = source_274 / "processed"
            failed_dir     = source_274 / "failed"
            active_file    = pending_274

            # Transition: Pending -> Inprogress
            os.makedirs(inprogress_dir, exist_ok=True)
            inprogress_file = inprogress_dir / active_file.name
            print(f"Moving file to execution phase: {inprogress_file}")
            shutil.move(str(active_file), str(inprogress_file))
            active_file = inprogress_file

            # Parse -> Map -> Convert
            structured_274     = EDIProcessor().parse(str(active_file))
            hierarchy_records  = mapper.map_hierarchy(structured_274)
            os.makedirs(output_274.parent, exist_ok=True)
            CSVConverter(schemas_dir=schemas_dir).convert_hierarchy(
                mapped_hierarchy=hierarchy_records,
                output_csv_path=str(output_274)
            )
            print(f"Directory processing complete. Output: {output_274}")

            # Transition: Inprogress -> Processed
            os.makedirs(processed_dir, exist_ok=True)
            processed_file = processed_dir / active_file.name
            shutil.move(str(active_file), str(processed_file))
            print(f"Moving file to completion phase: {processed_file}")

    except Exception as e:
        print(f"Directory (274) pipeline failed: {e}")
        raise e


if __name__ == "__main__":
    main()
