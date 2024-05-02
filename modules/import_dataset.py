import logging
import dtlpy as dl

logger = logging.getLogger(name='dataset-importer')


class DatasetImporter(dl.BaseServiceRunner):
    def import_dataset(self, dataset: dl.Dataset, source: str):
        logger.info(f'getting system service to import dataset. service name: "public-exp-imp-service"')
        logger.info(f'dataset source is (src dataset name): {source}')
        import_dataset_service = dl.services.get(service_name='public-exp-imp-service')
        ex = import_dataset_service.execute(function_name="import_dataset",
                                            project_id=dataset.project.id,
                                            execution_input=[
                                                dl.FunctionIO(
                                                    type=dl.PackageInputType.DATASET,
                                                    name="dst_dataset",
                                                    value=dataset.id),
                                                dl.FunctionIO(
                                                    type=dl.PackageInputType.STRING,
                                                    name="src_dataset_name",
                                                    value=source
                                                )
                                            ])
        logger.info(f'Execution started to import dataset. ex id: {ex.id}')
        ex = ex.wait()
        # TODO raise error if ex failed
        logger.info(f'Execution finished with status {ex.latest_status}. ex id: {ex.id}')
        return dataset
