import logging
import shutil
import json
import os

import dtlpy as dl

logger = logging.getLogger('PublicDatasets')

RC_P_ID = "2bbf2d7e-0a04-4404-b264-91d4f929af26"
PROD_P_ID = ""
S_P_ID = ""


class DataloopDatasets(dl.BaseServiceRunner):
    def __init__(self):
        self.datasets_project = dl.projects.get(project_id=RC_P_ID)

    @staticmethod
    def deep_copy_dataset(src_dataset: dl.Dataset,
                          src_query: dict,
                          src_recipe: dl.Recipe,
                          dst_project: dl.Project,
                          dst_dataset: dl.Dataset = None):
        """

        :param src_dataset:
        :param src_query:
        :param src_recipe:
        :param dst_project:
        :param dst_dataset:
        :return:
        """

        if dst_dataset is None:
            dst_dataset = dst_project.datasets.create(dataset_name=src_dataset.name)

        dst_recipe: dl.Recipe = dst_dataset.recipes.list()[0]
        src_ont: dl.Ontology = src_recipe.ontologies.list()[0]
        dst_ont: dl.Ontology = dst_recipe.ontologies.list()[0]

        src_recipe.id = dst_recipe.id
        src_recipe.update(True)

        src_ont.id = dst_ont.id
        src_ont.update(True)

        tmp_dir = os.path.join('tmp', src_dataset.id)
        # download everything
        filters = None
        if src_query != {}:
            filters = dl.Filters(custom_filter=src_query)
        src_dataset.download(local_path=tmp_dir,
                             filters=filters,
                             annotation_options=['json'])
        # upload everything
        dst_dataset.items.upload(local_path=os.path.join(tmp_dir, 'items/*'),
                                 local_annotations_path=os.path.join(tmp_dir, 'json'))
        return dst_dataset

    def create_dpk_directory(self, dataset_name: str) -> str:
        src_app_dir = 'template_dataset_dpk'
        dst_app_dir = f'dataset_app_{dataset_name}'
        logger.info(f'creating DPK files from template: {src_app_dir!r} to {dst_app_dir!r}')
        shutil.copytree(src_app_dir, dst_app_dir)
        with open(os.path.join(dst_app_dir, 'dataloop.json'), 'r+') as f:
            manifest = f.read()
            manifest = manifest.replace("$DPK_DISPLAY_NAME", f"Dataloop Dataset {dataset_name}")
            manifest = manifest.replace("$DPK_NAME", f"dataloop-datasets-{dataset_name.lower().replace(' ', '-')}")
            manifest = manifest.replace("$DPK_DATASET_NAME", dataset_name)
            manifest = manifest.replace("$DPK_DATASET_DOCS", dataset_name)
            manifest = manifest.replace("$DPK_DATASET_SOURCE", dataset_name)
            f.seek(0)
            f.write(manifest)
            f.truncate()

        return dst_app_dir

    def import_to_main_project(self,
                               dataset_id: str,
                               query: dict = None,
                               dataset_name: str = None,
                               recipe_id: str = None,
                               overwrite: str = "false") -> dl.Dataset:
        dataset = dl.datasets.get(dataset_id=dataset_id)
        logger.info(f'Starting export: source dataset: {dataset.name!r}, {dataset.id!r}')
        if dataset_name is None:
            dataset_name = dataset.name
        overwrite = overwrite == "true"

        # check if dataset exists
        try:
            existing_dataset = self.datasets_project.datasets.get(dataset_name=dataset_name)
            if overwrite is False:
                raise ValueError(f'Dataset with same name already exists: {dataset.name}')
            else:
                # delete existing dataset for overwrite
                logger.warning(
                    f'Dataset exists and overwrite is {overwrite}. Deleting: {existing_dataset.name!r}, {existing_dataset.id!r}')
                existing_dataset.delete(True, True)
        except dl.exceptions.NotFound:
            pass

        if recipe_id is not None:
            src_recipe = dl.recipes.get(recipe_id=recipe_id)
        else:
            src_recipe: dl.Recipe = dataset.recipes.list()[0]
        if query is None:
            query = {}
        dst_dataset = self.deep_copy_dataset(src_dataset=dataset,
                                             src_query=query,
                                             src_recipe=src_recipe,
                                             dst_project=self.datasets_project)
        logger.info(f'dataset import finished. dst dataset: {dst_dataset.name!r}, {dst_dataset.id!r}')

        # create the DPK
        dpk_directory = self.create_dpk_directory(dataset_name=dataset.name)
        logger.info(f'DPK files created')

        # publish
        dpk = self.datasets_project.dpks.publish(ignore_max_file_size=True,
                                                 manifest_filepath=os.path.join(dpk_directory, 'dataloop.json'))
        logger.info(f'DPK published. dpk: {dpk.name!r}, {dpk.id!r}')

        return dst_dataset

    def import_dataset(self, dst_dataset: dl.Dataset, src_dataset_name: str) -> dl.Dataset:
        try:
            src_dataset = self.datasets_project.datasets.get(dataset_name=src_dataset_name)
        except dl.exceptions.NotFound:
            raise ValueError(f'Dataset with name {src_dataset_name!r} wasnt found in the public datasets project')
        src_recipe: dl.Recipe = src_dataset.recipes.list()[0]
        dst_dataset = self.deep_copy_dataset(src_dataset=src_dataset,
                                             src_recipe=src_recipe,
                                             src_query=dict(),
                                             dst_project=dst_dataset.project,
                                             dst_dataset=dst_dataset)
        return dst_dataset


if __name__ == "__main__":
    self = DataloopDatasets()
    self.import_to_main_project(dataset_id='5f4d13ba4a958a49a7747cd9')
