import logging
from pathlib import Path
from omegaconf import DictConfig, OmegaConf, open_dict


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ConfigValidator(object):
    def __init__(self, config: DictConfig):
        self.config = config
        OmegaConf.set_struct(self.config, True)

    def __call__(self):
        try:
            self.validate_model()
            self.validate_data()
            self.validate_episode()
            self.validate_visualizer()
            return self.config
        except ValueError:
            logger.error(f"Validation of config failed.")
            raise

    def validate_model(self):
        default = {"from_pretrained": "bert-base-uncased",
                   "layers": {"layer1": {
                        "n_in": 768,
                        "n_out": 20
                        }
                   },
                   "num_transformer_layers": 2,
                   "freeze_transformer_layers": None,
                   "learning_rate": 0.0001,
                   "dropout_rate": 0.5,
                   "epochs": 5,
                   "output_path": "./outputs/",
                   "contrastive": {
                       "contrastive_loss_ratio": 0,
                       "temperature": 0.07,
                       "base_temperature": 0.07,
                       "contrast_mode": "all"
                   },
                   "L2_normalize_encoded_feature": False
                   }
        self.create_output_path()
        with open_dict(self.config):
            for key, value in default.items():
                if key not in self.config.model:
                    logger.info(f"Validator: Key '{key}' not in config, adding the default value '{value}'.")
                    self.config.model.update({key: value})

    def validate_data(self):
        if "config" not in self.config.data:
            with open_dict(self.config):
                self.config.data.config = None
        if "validation" not in self.config.data:
            with open_dict(self.config):
                self.config.data.validation = False

    def validate_early_stopping(self):
        if "early_stopping" not in self.config:
            with open_dict(self.config):
                self.config.early_stopping = {}
        if "tolerance" not in self.config.early_stopping:
            with open_dict(self.config):
                self.config.early_stopping.tolerance = 5
        if "delta" not in self.config.early_stopping:
            with open_dict(self.config):
                self.config.early_stopping.delta = 0

    def validate_episode(self):
        pass

    def validate_visualizer(self):
        if "visualizer" not in self.config:
            with open_dict(self.config):
                self.config.visualizer = []

    def create_output_path(self):
        if not Path(self.config.model.output_path, self.config.name).absolute().exists():
            logger.warning(f"Output path {str(Path(self.config.model.output_path, self.config.name).absolute())} "
                            f"does not exist. It will be automatically created. ")
            Path(self.config.model.output_path, self.config.name).absolute().mkdir(parents=True, exist_ok=True)
        if not Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}").absolute().exists():
            Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}").absolute().mkdir(
                parents=True, exist_ok=True)
        if not Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}", "pretrained_models").absolute().exists():
            Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}", "pretrained_models").absolute().mkdir(parents=True, exist_ok=True)
        if not Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}", "plots").absolute().exists():
            Path(self.config.model.output_path, self.config.name, f"seed_{self.config.seed}", "plots").absolute().mkdir(parents=True, exist_ok=True)



