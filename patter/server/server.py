import grpc
import torch
import numpy as np
from marshmallow.exceptions import ValidationError

from . import speech_pb2, speech_pb2_grpc

from patter import ModelFactory
from patter.config import ServerConfiguration
from patter.data import AudioSegment
from patter.decoder import DecoderFactory
from patter.data.features import PerturbedSpectrogramFeaturizer


class SpeechServicer(speech_pb2_grpc.SpeechServicer):
    def __init__(self, model_path, decoder_config, language="en-US", cuda=False):
        # initialize the model to test
        self._model = ModelFactory.load(model_path)
        self._decoder = DecoderFactory.create(decoder_config, self._model.labels)
        self._featurizer = PerturbedSpectrogramFeaturizer.from_config(self._model.input_cfg)
        self._language = language
        self._use_cuda = cuda

        if self._use_cuda:
            self._model = self._model.cuda()

    def _raw_data_to_samples(self, data, sample_rate=16000, encoding=None):
        # TODO: support other encodings
        if sample_rate == 16000 and encoding == speech_pb2.RecognitionConfig.LINEAR16:
            signal = np.frombuffer(data, dtype=np.int16)
        else:
            raise ValueError("Unsupported audio data configuration")
            signal = None
        return signal

    def Recognize(self, request, context):
        print("Handling stream request...")
        config = request.config

        # check audio format (sample rate, encoding) to convert if necessary
        if config.language_code != self._language:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details('Requested unsupported language')
            return

        # get samples
        samples = self._raw_data_to_samples(request.audio.content, sample_rate=config.sample_rate_hertz, encoding=config.encoding)
        segment = AudioSegment(samples, config.sample_rate_hertz, target_sr=self._model.input_cfg['sample_rate'])
        features = self._featurizer.process_segment(segment)

        features = features.unsqueeze(0).unsqueeze(0)
        output, output_len = self._model(torch.autograd.Variable(features, requires_grad=False),
                                         torch.autograd.Variable(torch.IntTensor([[features.size(3)]]), requires_grad=False))

        decoded_output, _ = self._decoder.decode(output.transpose(0, 1).data, output_len.data)
        alternatives = []
        for path in decoded_output[0]:
            alternatives.append(speech_pb2.SpeechRecognitionAlternative(transcript=path, confidence=1.0))
        # may be multiple results if there are multiple chunks created
        results = [speech_pb2.SpeechRecognitionResult(alternatives=alternatives)]
        response = speech_pb2.RecognizeResponse(results=results)
        return response

    @classmethod
    def from_config(cls, server_config):
        try:
            cfg = ServerConfiguration().load(server_config)
            if len(cfg.errors) > 0:
                raise ValidationError(cfg.errors)
        except ValidationError as err:
            raise err
        return cls(cfg.data['model_path'], cfg.data['decoder'], language=cfg.data['language'], cuda=cfg.data['cuda'])


