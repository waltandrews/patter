from marshmallow import Schema, fields
from marshmallow.validate import Range


class AugmentationConfig(Schema):
    manifest_path = fields.String(load_from="manifest")
    min_snr_db = fields.Float()
    max_snr_db = fields.Float()
    min_speed_rate = fields.Float()
    max_speed_rate = fields.Float()
    min_shift_ms = fields.Float()
    max_shift_ms = fields.Float()
    min_gain_dbfs = fields.Float()
    max_gain_dbfs = fields.Float()


class AugmentationSpec(Schema):
    aug_type = fields.String(load_from="type", required=True)
    prob = fields.Float(required=True, validate=Range(0, 1))

    cfg = fields.Nested(AugmentationConfig, load_from="config")


class CorporaConfig(Schema):
    min_duration = fields.Float(missing=None)
    max_duration = fields.Float(missing=None)


class DatasetConfig(Schema):
    manifest = fields.String(required=True)
    name = fields.String(required=True)
    augment = fields.Boolean(required=False, default=False, missing=False)


class CorporaConfiguration(Schema):
    datasets = fields.Nested(DatasetConfig, load_from="dataset", many=True)
    cfg = fields.Nested(CorporaConfig, load_from="config")
    augmentation = fields.Nested(AugmentationSpec, many=True, missing=[])
