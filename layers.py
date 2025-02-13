import tensorflow as tf
from tensorflow.keras.layers import *
import typing
import tensorflow as tf


"""
Layers

This is only for implementing layers.
You should not import class or functions from modules or models
"""


def conv2d_bn(filters,
              kernel_size, 
              strides=(1, 1), 
              padding='same', 
              groups=1,
              use_bias=True, 
              kernel_regularizer=None, 
              activation='relu', 
              bn_args=None):
    if bn_args is None:
        bn_args = {} # you can put axis, momentum, epsilon in bn_args

    def _conv2d_layer(inputs):
        x = Conv2D(filters, kernel_size, 
                   strides=strides, 
                   padding=padding, 
                   groups=groups,
                   use_bias=use_bias, 
                   kernel_regularizer=kernel_regularizer)(inputs)
        x = BatchNormalization(**bn_args)(x)
        if activation:
            x = Activation(activation)(x)
        return x

    return _conv2d_layer


def force_1d_inputs():
    def force(inputs):
        x = inputs
        if len(x.shape) == 4:
            x = Reshape((-1, x.shape[-2]*x.shape[-1]))(x)
        return x
    return force


'''
POSITIONAL ENCODINGS
'''
def basic_pos_encoding(input_shape):
    # basic positional encoding from transformer
    k = input_shape[-1] // 2
    w = tf.reshape(tf.pow(10000, -tf.range(k)/k), (1, 1, -1))
    w = tf.constant(tf.cast(w, tf.float32))

    def pos_encoding(inputs):
        assert len(inputs.shape) == 3

        time = tf.shape(inputs)[-2]
        encoding = tf.reshape(tf.range(time, dtype=inputs.dtype), (1, -1, 1))
        encoding = tf.stack([tf.cos(w * encoding), tf.sin(w * encoding)], -1)
        encoding = tf.reshape(encoding, [1, *tf.shape(encoding)[1:-2], k*2])
        return encoding
    return pos_encoding


def rff_pos_encoding(input_shape):
    # pos encoding based on Random Fourier Features
    # RFF for 1D inputs (only time)
    k = input_shape[-1] // 2
    w = tf.constant(tf.random.normal([1, 1, k]))

    def pos_encoding(inputs):
        assert len(inputs.shape) == 3

        time = tf.shape(inputs)[-2]
        encoding = tf.reshape(tf.range(time, dtype=inputs.dtype), (1, -1, 1))
        encoding = tf.concat([tf.cos(w * encoding), tf.sin(w * encoding)], -1)
        return encoding
    return pos_encoding

# Copyright 2020 Huy Le Nguyen (@usimarit)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# https://github.com/TensorSpeech/TensorFlowASR/blob/main/tensorflow_asr/models/layers/multihead_attention.py


class MultiHeadAttention_(tf.keras.layers.Layer):
    def __init__(self,
                 num_heads,
                 head_size,
                 output_size: int = None,
                 dropout: float = 0.0,
                 return_attn_coef: bool = False,
                 use_bias: bool = True, 
                 kernel_initializer: typing.Union[str, typing.Callable] = "glorot_uniform",
                 kernel_regularizer: typing.Union[str, typing.Callable] = None,
                 kernel_constraint: typing.Union[str, typing.Callable] = None,
                 bias_initializer: typing.Union[str, typing.Callable] = "zeros",
                 bias_regularizer: typing.Union[str, typing.Callable] = None,
                 bias_constraint: typing.Union[str, typing.Callable] = None,
                 **kwargs):
        super(MultiHeadAttention_, self).__init__(**kwargs)

        if output_size is not None and output_size < 1:
            raise ValueError("output_size must be a positive number")

        self.kernel_initializer = tf.keras.initializers.get(kernel_initializer)
        self.kernel_regularizer = tf.keras.regularizers.get(kernel_regularizer)
        self.kernel_constraint = tf.keras.constraints.get(kernel_constraint)
        self.bias_initializer = tf.keras.initializers.get(bias_initializer)
        self.bias_regularizer = tf.keras.regularizers.get(bias_regularizer)
        self.bias_constraint = tf.keras.constraints.get(bias_constraint)

        self.use_bias = use_bias
        self.head_size = head_size
        self.num_heads = num_heads
        self.output_size = output_size
        self.use_projection_bias = use_bias
        self.return_attn_coef = return_attn_coef

        self.dropout = tf.keras.layers.Dropout(dropout, name="dropout")
        self._droput_rate = dropout

    def build(self, input_shape):
        num_query_features = input_shape[0][-1]
        num_key_features = input_shape[1][-1]
        num_value_features = (
            input_shape[2][-1] if len(input_shape) > 2 else num_key_features
        )
        output_size = (
            self.output_size if self.output_size is not None else num_value_features
        )
        self.query_kernel = self.add_weight(
            name="query_kernel",
            shape=[self.num_heads, num_query_features, self.head_size],
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
        )
        self.key_kernel = self.add_weight(
            name="key_kernel",
            shape=[self.num_heads, num_key_features, self.head_size],
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
        )
        self.value_kernel = self.add_weight(
            name="value_kernel",
            shape=[self.num_heads, num_value_features, self.head_size],
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
        )
        self.projection_kernel = self.add_weight(
            name="projection_kernel",
            shape=[self.num_heads, self.head_size, output_size],
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint,
        )
        if self.use_projection_bias:
            self.projection_bias = self.add_weight(
                name="projection_bias",
                shape=[output_size],
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
            )
        if self.use_bias:
            self.q_bias = self.add_weight(
                name="q_bias",
                shape=[self.num_heads, self.head_size],
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
            )
            self.k_bias = self.add_weight(
                name="k_bias",
                shape=[self.num_heads, self.head_size],
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
            )            
            self.v_bias = self.add_weight(
                name="v_bias",
                shape=[self.num_heads, self.head_size],
                initializer=self.bias_initializer,
                regularizer=self.bias_regularizer,
                constraint=self.bias_constraint,
            )
        else:
            self.projection_bias = None

    def call_qkv(self, query, key, value, training=False):
        # verify shapes
        if key.shape[-2] != value.shape[-2]:
            raise ValueError(
                "the number of elements in 'key' must be equal to "
                "the same as the number of elements in 'value'"
            )
        # Linear transformations
        query = tf.einsum("...NI,HIO->...NHO", query, self.query_kernel)
        key = tf.einsum("...MI,HIO->...MHO", key, self.key_kernel)
        value = tf.einsum("...MI,HIO->...MHO", value, self.value_kernel)

        if self.use_bias:
            query = query + self.q_bias
            key = key + self.k_bias
            value = value + self.v_bias
        return query, key, value

    def call_attention(self, query, key, value, logits, training=False, mask=None):
        # mask = attention mask with shape [B, Tquery, Tkey] with 1 is for positions we want to attend, 0 for masked
        if mask is not None:
            if len(mask.shape) < 2:
                raise ValueError("'mask' must have at least 2 dimensions")
            if query.shape[-3] != mask.shape[-2]:
                raise ValueError(
                    "mask's second to last dimension must be equal to "
                    "the number of elements in 'query'"
                )
            if key.shape[-3] != mask.shape[-1]:
                raise ValueError(
                    "mask's last dimension must be equal to the number of elements in 'key'"
                )
        # apply mask
        if mask is not None:
            mask = tf.cast(mask, tf.float32)

            # possibly expand on the head dimension so broadcasting works
            if len(mask.shape) != len(logits.shape):
                mask = tf.expand_dims(mask, -3)

            logits += -10e9 * (1.0 - mask)

        attn_coef = tf.nn.softmax(logits)

        # attention dropout
        attn_coef_dropout = self.dropout(attn_coef, training=training)

        # attention * value
        multihead_output = tf.einsum("...HNM,...MHI->...NHI", attn_coef_dropout, value)

        # Run the outputs through another linear projection layer. Recombining heads
        # is automatically done.
        output = tf.einsum("...NHI,HIO->...NO", multihead_output, self.projection_kernel)

        if self.projection_bias is not None:
            output += self.projection_bias

        return output, attn_coef

    def call(self, inputs, training=False, mask=None, **kwargs):
        query, key, value = inputs

        query, key, value = self.call_qkv(query, key, value, training=training)

        # Scale dot-product, doing the division to either query or key
        # instead of their product saves some computation
        depth = tf.constant(self.head_size, dtype=tf.float32)
        query /= tf.sqrt(depth)

        # Calculate dot product attention
        logits = tf.einsum("...NHO,...MHO->...HNM", query, key)

        output, attn_coef = self.call_attention(query, key, value, logits,
                                                training=training, mask=mask)

        if self.return_attn_coef:
            return output, attn_coef
        else:
            return output

    def compute_output_shape(self, input_shape):
        num_value_features = (
            input_shape[2][-1] if len(input_shape) > 2 else input_shape[1][-1]
        )
        output_size = (
            self.output_size if self.output_size is not None else num_value_features
        )

        output_shape = input_shape[0][:-1] + (output_size,)

        if self.return_attn_coef:
            num_query_elements = input_shape[0][-2]
            num_key_elements = input_shape[1][-2]
            attn_coef_shape = input_shape[0][:-2] + (
                self.num_heads,
                num_query_elements,
                num_key_elements,
            )

            return output_shape, attn_coef_shape
        else:
            return output_shape

    def get_config(self):
        config = super().get_config()

        config.update(
            head_size=self.head_size,
            num_heads=self.num_heads,
            output_size=self.output_size,
            dropout=self._droput_rate,
            return_attn_coef=self.return_attn_coef,
            kernel_initializer=tf.keras.initializers.serialize(self.kernel_initializer),
            kernel_regularizer=tf.keras.regularizers.serialize(self.kernel_regularizer),
            kernel_constraint=tf.keras.constraints.serialize(self.kernel_constraint),
            bias_initializer=tf.keras.initializers.serialize(self.bias_initializer),
            bias_regularizer=tf.keras.regularizers.serialize(self.bias_regularizer),
            bias_constraint=tf.keras.constraints.serialize(self.bias_constraint),
        )

        return config


class RelPositionMultiHeadAttention(MultiHeadAttention_):
    def build(self, input_shape):
        num_pos_features = input_shape[-1][-1]
        
        self.pos_kernel = self.add_weight(
            name="pos_kernel",
            shape=[self.num_heads, num_pos_features, self.head_size],
            initializer=self.kernel_initializer,
            regularizer=self.kernel_regularizer,
            constraint=self.kernel_constraint
        )            
        self.pos_bias_u = self.add_weight(
            name="pos_bias_u",
            shape=[self.num_heads, self.head_size],
            regularizer=self.kernel_regularizer,
            initializer=self.kernel_initializer,
            constraint=self.kernel_constraint
        )
        self.pos_bias_v = self.add_weight(
            name="pos_bias_v",
            shape=[self.num_heads, self.head_size],
            regularizer=self.kernel_regularizer,
            initializer=self.kernel_initializer,
            constraint=self.kernel_constraint
        )
        super(RelPositionMultiHeadAttention, self).build(input_shape[:-1])

    @staticmethod
    def relative_shift(x):
        x_shape = tf.shape(x)
        x = tf.pad(x, [[0, 0], [0, 0], [0, 0], [1, 0]])
        x = tf.reshape(x, [x_shape[0], x_shape[1], x_shape[3] + 1, x_shape[2]])
        x = tf.reshape(x[:, :, 1:, :], x_shape)
        return x

    def call(self, inputs, training=False, mask=None, **kwargs):
        query, key, value, pos = inputs

        query, key, value = self.call_qkv(query, key, value, training=training)

        pos = tf.einsum("...MI,HIO->...MHO", pos, self.pos_kernel)

        query_with_u = query + self.pos_bias_u
        query_with_v = query + self.pos_bias_v

        logits_with_u = tf.einsum("...NHO,...MHO->...HNM", query_with_u, key)
        logits_with_v = tf.einsum("...NHO,...MHO->...HNM", query_with_v, pos)
        logits_with_v = self.relative_shift(logits_with_v)

        logits = logits_with_u + logits_with_v[:, :, :, :tf.shape(logits_with_u)[3]]

        depth = tf.constant(self.head_size, dtype=tf.float32)
        logits /= tf.sqrt(depth)

        output, attn_coef = self.call_attention(query, key, value, logits, 
                                                training=training, mask=mask)

        if self.return_attn_coef:
            return output, attn_coef
        else:
            return output
