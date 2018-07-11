import os

from keras import backend as K
from keras import layers as KL
from keras import data as KD
from keras import models as KM

class MaskTrajectory(object):

    name = 'mask_trajectory'
    relu_max = 6

    def __init__(self, mode, config, model_dir,
        debugging=False, optimizer=keras.optimizers.Adadelta(),
        loss_function=keras.losses.binary_cross_entropy):
        """
        Creates and builds the mask propagation network.
        :param mode: either 'training' or 'inference'
        :param config: not used atm
        :param model_dir: directory to save/load logs and model checkpoints
        :param debugging: whether to include extra print operations
        :param optimizer: keras optimizer object,
          e.g. keras.optimizers.Adadelta()
        :param loss_function: a (could be Keras) function that computes the loss between
          the predicted and gt masks
        """
        self.mode = mode
        self.model_dir = model_dir
        self.config = config
        self.weights_path = config.weights_path if config else None

        self.debugging = debugging

        self.optimizer = optimizer
        self.loss_function = loss_function
        
        self.epoch = 0

        assert mode in ['training', 'inference']

        self.keras_model = self._build()

    def _build(self):
        """
        Builds the mask trajectory network.
        """

        flow_field = Input(shape=(None, None, None, 2))
        prev_mask = Input(shape=(None, None, None, 1))
        inputs = [flow_field, prev_mask]

        x = KL.Concatenate(inputs, axis=3, name='L0_concat')

        # build the u-net and get the final propagated mask
        x = self._build_unet(x)
        self.propagated_masks = x

        model = KM.Model(inputs, outputs, name='mask_rcnn')

        model = KM.Model(inputs, outputs, name='mask_rcnn')

        if self.weights_path:

            model.load_weights(weights_path)

        return model

    # relu with max value defined by the variable relu_max
    def m_relu(x):

        return K.relu(x, max_value=relu_max)

    def _build_unet(self, x, conv_act=m_relu, deconv_act=None):
        """
        Builds the mask propagation network proper
          (based on the u-Net architecture).
        :param x: input tensor of the mask and flow field concatenated
          [batch, w, h, 1+2]
        :param conv_act: activation function for the convolution layers
        :param deconv_act: activation function for
          the transposed convolution layers
        :return: output tensor of the U-Net [batch, w, h, 1]
          As a side effect, two instance variables unet_left_wing and
          unet_right_wing are set with the final output tensors
          for each layer of the two halves of the U.
        """

        _input = x

        x = KL.Conv2D(64, (3, 3), activation=conv_act, name='L1_conv1')(x)
        x = KL.Conv2D(64, (3, 3), activation=conv_act, name='L1_conv2')(x)
        L1 = x

        x = KL.MaxPooling2D( (2, 2), (2, 2), name='L2_pool')(x)
        x = KL.Conv2D( 128, (3, 3), activation=conv_act, name='L2_conv1')(x)
        x = KL.Conv2D( 128, (3, 3), activation=conv_act, name='L2_conv2')(x)
        L2 = x

        x = KL.MaxPooling2D( (2, 2), (2, 2), name='L3_pool')
        x = KL.Conv2D( 256, (3, 3), activation=conv_act, name='L3_conv1')(x)
        x = KL.Conv2D( 256, (3, 3), activation=conv_act, name='L3_conv2')(x)
        L3 = x

        x = KL.MaxPooling2D( (2, 2), (2, 2), name='L4_pool')
        x = KL.Conv2D( 512, (3, 3), activation=conv_act, name='L4_conv1')(x)
        x = KL.Conv2D( 512, (3, 3), activation=conv_act, name='L4_conv2')(x)
        L4 = x

        x = KL.MaxPooling2D( (2, 2), (2, 2), name='L5_pool')(x)
        x = KL.Conv2D( 1024, (3, 3), activation=conv_act, name='L5_conv1')(x)
        x = KL.Conv2D( 1024, (3, 3), activation=conv_act, name='L5_conv2')(x)
        L5 = x

        x = KL.Conv2DTranspose( 1024, (2, 2), strides=(2, 2),
            activation=deconv_act, name='P4_upconv')(x)
        x = KL.Concatenate([L4, K.resize_images( tf.shape(L4)[1:3])],
                      axis=3, name='P4_concat')(x)
        x = KL.Conv2D( 512, (3, 3), activation=conv_act, name='P4_conv1')(x)
        x = KL.Conv2D( 512, (3, 3), activation=conv_act, name='P4_conv2')(x)
        P4 = x

        x = KL.Conv2DTranspose( 512, (2, 2), strides=(2, 2),
            activation=deconv_act, name='P3_upconv')(x)
        x = tf.concat([L3, tf.image.resize_images( tf.shape(L3)[1:3])],
                      axis=3, name='P3_concat')(x)
        x = KL.Conv2D( 256, (3, 3), activation=conv_act, name='P3_conv1')(x)
        x = KL.Conv2D( 256, (3, 3), activation=conv_act, name='P3_conv2')(x)
        P3 = x

        x = KL.Conv2DTranspose( 256, (2, 2), strides=(2, 2),
            activation=deconv_act, name='P2_upconv')(x)
        x = tf.concat([L2, tf.image.resize_images( tf.shape(L2)[1:3])],
                      axis=3, name='P2_concat')(x)
        x = KL.Conv2D( 128, (3, 3), activation=conv_act, name='P2_conv1')(x)
        x = KL.Conv2D( 128, (3, 3), activation=conv_act, name='P2_conv2')(x)
        P2 = x

        x = KL.Conv2DTranspose( 128, (2, 2), strides=(2, 2),
            activation=deconv_act, name='P1_upconv')(x)
        x = tf.concat([L1, tf.image.resize_images( tf.shape(L1)[1:3])],
                      axis=3, name='P1_concat')(x)
        x = KL.Conv2D( 64, (3, 3), activation=conv_act, name='P1_conv1')(x)
        x = KL.Conv2D( 64, (3, 3), activation=conv_act, name='P1_conv2')(x)
        P1 = x

        x = tf.image.resize_images( tf.shape(_input)[1:3])(x)
        x = KL.Conv2D( 1, (1, 1), activation=tf.sigmoid, name='P0_conv')(x)

        self.unet_left_wing = [L1, L2, L3, L4, L5]
        self.unet_right_wing = [P4, P3, P2, P1]

        return x

    def compile(self):

        self.keras_model.compile(optimizer=self.optimizer,
                                 loss=self.loss_function)

#     def train_batch(self, flow_field, prev_masks):

    #MAJOR WORK IN PROGRESS
    def train_multi_step(self, train_generator, val_generator, epochs, steps_per_epoch, batch_size):
        """THIS IS WORK IN PROGRESS. DO NOT USE YET
        Trains the mask propagation network on multiple steps (batches).
        (Essentially an epoch.)
        :param train_dataset: Training Dataset object
        :param steps: Number of times to call the generator.
          (Number of steps in this "epoch".)
        :param batch_size: A tf.int64 scalar tf.Tensor, representing the number
          of consecutive elements of the generator to combine in a single batch.
        :param output_types: output_types: A nested structure of
          tf.DType objects corresponding to each component of an element yielded
          by generator.
        :param output_shapes: (Optional.) A nested structure of tf.TensorShape
          objects corresponding to each component of an element yielded by
          generator.
        :return: a list of batch losses of the predicted masks against the
          generated ground truths
        """
        
        # Work-around for Windows: Keras fails on Windows when using
        # multiprocessing workers. See discussion here:
        # https://github.com/matterport/Mask_RCNN/issues/13#issuecomment-353124009
        if os.name is 'nt':
            workers = 0
        else:
            workers = max(batch_size // 2, 2)

        self.keras_model.fit_generator(
            train_generator,
            initial_epoch=self.epoch,
            epochs=epochs,
            steps_per_epoch=steps_per_epoch,
#             callbacks=callbacks,
            validation_data=val_generator,
            validation_steps=self.config.VALIDATION_STEPS,
            max_queue_size=100,
            workers=workers,
            use_multiprocessing=True,
        )
        self.epoch = max(self.epoch, epochs)

    def inference(self, flow_field, prev_mask):
        """
        Evaluates the model to get the flow field between the two images.
        :param prev_image: starting image for flow [w, h, 3]
        :param curr_image: ending image for flow [w, h, 3]
        :return: flow field for the images [batch, w, h, 2]
        """

        assert self.mode == 'inference'

        inputs = [flow_field, prev_mask]
        
        mask = self.keras_model.predict(inputs, verbose=0)

        return mask

    def save_weights(self, filename):
        weights_pathname = os.path.join(self.model_dir, filename)
        
        self.keras_model.save_weights(weights_pathname)

    def load_weights(self, filename, by_name=False):
        weights_pathname = os.path.join(self.model_dir, filename)

        self.keras_model.load_weights(weights_pathname, by_name)
