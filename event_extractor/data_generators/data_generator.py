from copy import deepcopy
from typing import Optional, Dict
import datasets
from datasets import load_dataset, concatenate_datasets, ClassLabel, Features, Dataset
from omegaconf import DictConfig
from torch.utils.data import DataLoader, Sampler, RandomSampler

datasets.logging.set_verbosity_info()


class OOSDatasetGenerator(object):
    def __init__(self, cfg: DictConfig, features: Features):
        self.cfg = cfg
        self.features = features

    @property
    def updated_features(self) -> Features:
        duplicated_features = deepcopy(self.features)
        duplicated_features["label"] = ClassLabel(names=self.features["label"].names + ["oos"],
                                                  num_classes=self.features["label"].num_classes + 1)
        return duplicated_features

    def oos_dataset(self, mode: str):
        def change_label(example):
            example["label"] = self.features["label"].num_classes
            return example
        datasets = [load_dataset("tweet_eval", "emoji", split=mode),
                    load_dataset("tweet_eval", "emotion", split=mode),
                    load_dataset("tweet_eval", "sentiment", split=mode),
                    load_dataset("tweet_eval", "hate", split=mode),
                    load_dataset("tweet_eval", "offensive", split=mode),
                    load_dataset("tweet_eval", "irony", split=mode),
                    load_dataset("tweet_eval", "stance_abortion", split=mode),
                    load_dataset("tweet_eval", "stance_atheism", split=mode),
                    load_dataset("tweet_eval", "stance_climate", split=mode),
                    load_dataset("tweet_eval", "stance_feminist", split=mode),
                    load_dataset("tweet_eval", "stance_hillary", split=mode)
                    ]
        aligned_datasets = list(map(lambda x: x.cast(self.updated_features), datasets))
        concatenated_dataset = concatenate_datasets(aligned_datasets).train_test_split(test_size=0.1)["test"]
        updated_dataset = concatenated_dataset.map(change_label)
        return updated_dataset

    def include_oos(self, dataset, mode: str) -> Dataset:
        aligned_datasets = list(map(lambda x: x.cast(self.updated_features), [dataset, self.oos_dataset(mode)]))
        dataset_with_oos = concatenate_datasets(aligned_datasets)
        return dataset_with_oos


class DataGenerator(object):
    def __init__(self, cfg: DictConfig):
        self.cfg = cfg
        self.oos_generator = None
        task = "multi-class" if cfg.data.classes else "multi-label"
        if cfg.data.include_oos:
            self.oos_generator = OOSDatasetGenerator(cfg, deepcopy(self.testing_dataset.features))
            self.num_labels = self.oos_generator.updated_features['label'].num_classes
            self.label_index_map: Dict = {label: self.oos_generator.updated_features['label'].str2int(label)
                                          for label in self.oos_generator.updated_features['label'].names}
        else:
            if task == "multi-class":
                self.num_labels = len(cfg.data.classes)
                self.label_index_map: Dict = {label: i
                                              for i, label in enumerate(cfg.data.classes)}
            elif task == "multi-label":
                self.num_labels = self.training_dataset.features['label'].num_classes
                self.label_index_map: Dict = {label: self.training_dataset.features['label'].str2int(label)
                                              for label in self.training_dataset.features['label'].names}
            else:
                raise ValueError

    @property
    def training_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='train')
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        if self.oos_generator:
            dataset = self.oos_generator.include_oos(dataset, "train")
        return dataset

    @property
    def validation_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='validation')
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        if self.oos_generator:
            dataset = self.oos_generator.include_oos(dataset, "validation")
        return dataset

    @property
    def testing_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='test')
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        if self.oos_generator:
            dataset = self.oos_generator.include_oos(dataset, "test")
        return dataset

    @staticmethod
    def rename_column(dataset, original_label_name, new_label_name):
        return dataset.rename_column(original_label_name, new_label_name)

    def __call__(self,
                 mode: str,
                 batch_size: Optional[int] = None,
                 sampler: Optional[Sampler] = None) -> DataLoader:
        """
        :param mode: train, valid or test
        :param batch_size:
        :param shuffle:
        :param sampler:
        :return:
        """
        batch_size = batch_size or self.cfg.data.batch_size
        if mode == "train":
            dataset = self.training_dataset
        elif mode == "test":
            dataset = self.testing_dataset
        elif mode == "validation":
            dataset = self.validation_dataset
        else:
            raise AttributeError(f"{mode} is not a valid attribute in Data Generator class.")
        # default sampler is a random sampler over all entries in the dataset.
        sampler = sampler or RandomSampler(dataset)
        return DataLoader(dataset, batch_size=batch_size, sampler=sampler)


class DataGeneratorSubSample(DataGenerator):
    @property
    def training_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='train').train_test_split(test_size=self.cfg.data.subset)["test"]
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        return dataset

    @property
    def testing_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='test').train_test_split(test_size=self.cfg.data.subset)["test"]
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        return dataset

    @property
    def validation_dataset(self):
        dataset = load_dataset(self.cfg.data.name, self.cfg.data.config, split='validation').train_test_split(test_size=self.cfg.data.subset)["test"]
        if self.cfg.data.label_column != 'label':
            dataset = self.rename_column(dataset, self.cfg.data.label_column, 'label')
        if self.cfg.data.text_column != 'text':
            dataset = self.rename_column(dataset, self.cfg.data.text_column, 'text')
        return dataset
