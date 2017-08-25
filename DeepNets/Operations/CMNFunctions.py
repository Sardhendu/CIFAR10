from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time

# Model Packages importA
import numpy as np
import pandas as pd
import tensorflow as tf



def convLinearActivation(xIN, convKernelSize, convStride, inpDepth, outDepth,
                         padding, params=None, scope=None):
    """
    :param xIN:             The input X
    :param convKernelSize:  The Kernel size or the filter size (the dimensions should be equal) Ex: (3,3)
    :param convStride   : How many strides
    :param inpDepth:    The input depth, or the number of filters, for first layer impDept == numChannels
    :param outDepth:    The output depth of the Convolution layer or number of filters
    :param params:      Other  params such as mean stddev for gaussian dist
    :param scope:       The name of the scope
    :return:
    """
    wMean = params['wMean']
    wStdev = params['wStdev']
    wSeed = params['wSeed']
    bSeed = params['wSeed']


    with tf.variable_scope(scope or "convLinear-activation"):
        w = tf.get_variable(
                dtype='float32',
                shape=[convKernelSize[0], convKernelSize[1], inpDepth, outDepth],
                initializer=tf.random_normal_initializer(
                        mean=wMean, stddev=wStdev, seed=wSeed
                ),
                name="convWeight"
        )


        b = tf.get_variable(
                dtype='float32',
                shape=[outDepth],
                initializer=tf.random_normal_initializer(1.0, seed=bSeed),
                name="convBias"
                
        )
        
        print (w.get_shape())
        print (b.get_shape())
        print (xIN.get_shape())

        return tf.nn.conv2d(xIN, w, [1, convStride, convStride, 1], padding=padding) + b # Same padding
        # return = tf.nn.bias_add(x, b)
    
# class Activations():
def linearActivation(xIN, numInp, numOut, params, scope=None):
    """
    :param x:           Input Data
    :param numInp:      number of inputs units
    :param numOut:      number of output units
    :param params:      parameters for linear function Examples {wMean=0.0, wStdev=0.1, wSeed=6432, bSeed=928}
    :param scope:       Scope name (Layer1 or Layer2 depending on what your layer is)
    :return:            A computational graph of the processes of the linear activation
    """
    wMean = params['wMean']
    wStdev = params['wStdev']
    wSeed = params['wSeed']
    bSeed = params['wSeed']

    with tf.variable_scope(scope or "linear-activation"):
        w = tf.get_variable(
                dtype='float32',
                shape=[numInp, numOut],
                initializer=tf.random_normal_initializer(
                        mean=wMean, stddev=wStdev, seed=wSeed),
                name='weight')
        
        b = tf.get_variable(
                dtype='float32',
                shape=[numOut],
                initializer=tf.constant_initializer(1.0),
                name='bias')
        
        return tf.matmul(xIN, w) + b




def batchNorm(xIN, numOut,
              training_phase,
              mAvg_decay=0.5,
              epsilon=1e-4,
              axes=[0],
              scope=None):
    """
    :param x:           The input after linear activation
    :param numOut:      Basically the number of Columns for the input matrix
    :param mAvg_decay:  The moving average decay
                        In many application it is important to keep a moving average of trained variable because
                        sometimes
                        average produce better result than the final value.
                        shadow_variable = decay * shadow_variable + (1 - decay) * variable
                        Here variable contains the new value of the trained variable
                        Here shadow variable contains the moving average till last training point
    :param axes:        For global normalization such as CNN ith [batch, height, width, depth]  pass axes=[0,1,1]
                        For simple batch normalization pass axes=[0]
    :param scope:      The scope name
    :return:           The normed output of from the batch norm layer
    
    : NOTE: The below code can also be written in one line, for example
    tf.nn.batch_normalization(xIN,
                              batch_mean,batch_var,
                              beta,gamma,
                              epsilon)
                              
    But the below equation type code is a better representation for understanding
    
    The parameter beta, gamma and new input xIN are learned via back propagation
    """
    # First we need to find the Batch mean and standard deviation column wise
    with tf.variable_scope(scope or "batchNorm-Layer"):
        # Initialize parameters for Batch Norm
        beta = tf.get_variable(
                dtype='float32',
                shape=[numOut],
                initializer = tf.constant_initializer(0.0),
                name="beta",
                trainable=True
        )
        gamma = tf.get_variable(
                dtype='float32',
                shape=[numOut],
                initializer=tf.constant_initializer(1.0),
                name="gamma",
                trainable=True)
        
        # batchMean is an array of Hidden size with mean of each column
        # batchVar is an array of Hidden size with variance of each column
        batchMean, batchVar= tf.nn.moments(xIN, axes, name="moments")
        
        # Initialize the Moving Average model
        ema = tf.train.ExponentialMovingAverage(decay=mAvg_decay)

        # Apply the moving average only for the training Data, not for the cross validation or test data
        def updateMeanVariance():
            # The .apply([list]) function creates the shadow variable for all elements in the list
            # Shadow variables for `Variable` objects are initialized to the variable's initial value.
            maintain_averages_op = ema.apply([batchMean, batchVar])
            # The below takes care of running all the dependency
            with tf.control_dependencies([maintain_averages_op]):
                return tf.identity(batchMean), tf.identity(batchVar)

        
        # The below is analogous to if else condition statement,
        # Basically we don't want to perform the moving average for validation
        # dataset. So we condition that if training_phase is True then we perform
        # mean_var_with_update, Else we print ('11111111')just use the ema (estimated moving average)
        # for both batch_mean and batch_var trained till this point
        mean, var = tf.cond(training_phase,
                            updateMeanVariance,
                            lambda: (ema.average(batchMean), ema.average(batchVar)))
        
        # Normalize the Batch
        bn = (xIN-mean) / tf.sqrt(var + epsilon)

        
        # Scale and shift the normalization, if required
        bnOUT = gamma*bn + beta
        
        return bnOUT, batchMean, batchVar, mean, var
    

def nonLinearActivation(xIN, activation='RELU', scope=None):
    """
    :param x:           The linear activation input/Batch norm input
    :param activation:  The activation unit (RELU/LOGIT)
    :param scope:       Scope name (should be same as the linearActivation scope)
    :return:            The output after applying the non linear activation
    """
    with tf.variable_scope(scope or "nonLinear-activation"):
        if activation=="RELU":
            return tf.nn.relu(xIN)
        elif activation=="LOGIT":
            return tf.sigmoid(xIN)


def poolLayer(xIN, poolKernelSize, poolStride, padding, poolType='MAX', scope=None):
    """
    :param xIN:                 The input X
    :param poolKernelSize:      The pooling kernel or filter size, Ex : (2,2)
    :param poolStride:          The pooling Stride or filter stride Ex ; (1,1)
    :param padding:             padding normally "SAME"
    :param poolType:            The pool type "Average pooling or max pooling"
    :param scope:               The name of the scope
    :return:
    """

    with tf.variable_scope(scope or "Pool-Layer"):
        if poolType == 'MAX':
            return tf.nn.max_pool(xIN,
                                  ksize=[1, poolKernelSize[0],
                                         poolKernelSize[1], 1],
                                  strides=[1, poolStride, poolStride, 1],
                                  padding=padding)
        elif poolType == 'AVG':
            return tf.nn.avg_pool(xIN,
                                  ksize=[1, poolKernelSize, poolKernelSize, 1],
                                  strides=[1, poolStride, poolStride, 1],
                                  padding=padding)
        


def outSoftmaxActivation(xIN, numInp, numOut, params, scope=None):
    wMean = params['wMean']
    wStdev = params['wStdev']
    wSeed = params['wSeed']
    bSeed = params['wSeed']
    
    with tf.variable_scope(scope or "linear-activation"):
        w = tf.get_variable(
                dtype='float32',
                shape=[numInp, numOut],
                initializer=tf.random_normal_initializer(
                        mean=wMean, stddev=wStdev, seed=wSeed),
                name='weight')
        
        b = tf.get_variable(
                dtype='float32',
                shape=[numOut],
                initializer=tf.constant_initializer(1.0),
                name='bias')
        
        outState = tf.matmul(xIN, w) + b
    
        return outState, tf.nn.softmax(outState)


def lossOptimization(xIN, yIN, optimimzerParam=dict(optimimzer="ADAM", learning_rate=0.0001)):
    lossCE = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=xIN, labels=yIN))
    
    if optimizerParam['optimizer'] == 'ADAM':
        optimizer = tf.train.AdamOptimizer(learning_rate=optimizerParam['learning_rate']).minimize(lossCE)
    elif optimizerParam['optimizer'] == 'RMSPROP':
        optimizer = tf.train.RMSPropOptimizer(learning_rate=optimizerParam['learning_rate'],
                                              momentum=optimizerParam['momentum']).minimize(lossCE)  # 0.0006  # 0.8
    else:
        print("Your provided optimizers do not match with any of the initialized optimizers: .........")
        return None

    return optimizer