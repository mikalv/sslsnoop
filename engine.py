#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Loic Jaquemet loic.jaquemet+python@gmail.com
#

__author__ = "Loic Jaquemet loic.jaquemet+python@gmail.com"

import os,logging,sys, copy

import ctypes, model
from ctypes import cdll
from ctypes_openssh import AES_BLOCK_SIZE, ssh_aes_ctr_ctx
from ctypes_openssl import AES_KEY

log=logging.getLogger('engine')

libopenssl=cdll.LoadLibrary('libssl.so')


class Engine:

  def decrypt(self,block):
    ''' decrypts '''
    bLen=len(block)
    if bLen % AES_BLOCK_SIZE:
      log.error("Sugar, why do you give me a block the wrong size: %d not modulo of %d"%(bLen, AES_BLOCK_SIZE))
      return None
    data=(ctypes.c_ubyte*bLen )()
    for i in range(0, bLen ):
      #print i, block[i] 
      data[i]=ord(block[i])
    # no way....
    return self._decrypt(data,bLen)
  
  def _decrypt(self,data,bLen):
    raise NotImplementedError


def myhex(bstr):
  s=''
  for el in bstr:
    s+='\\'+hex(ord(el))[1:]
  return s

class StatefulAESEngine(Engine):
  #ctx->cipher->do_cipher(ctx,out,in,inl);
  # -> openssl.AES_ctr128_encrypt(&in,&out,length,&aes_key, ivecArray, ecount_bufArray, &num )
  #AES_encrypt(ivec, ecount_buf, key); # aes_key is struct with cnt, key is really AES_KEY->aes_ctx
  #AES_ctr128_inc(ivec); #ssh_Ctr128_inc semble etre different, mais paramiko le fait non ?
  def __init__(self, context ):
    self.sync(context)
    self._AES_ctr=libopenssl.AES_ctr128_encrypt
    log.debug('cipher:%s block_size: %d key_len: %d '%(context.name, context.block_size, context.key_len))
  
  def _decrypt(self,block, bLen):
    buf=(ctypes.c_ubyte*AES_BLOCK_SIZE)()
    dest=(ctypes.c_ubyte*bLen)()
    num=ctypes.c_uint()
    ##log.debug('BEFORE %s'%( myhex(self.aes_key_ctx.getCounter())) )
    #void AES_ctr128_encrypt(
    #      const unsigned char *in, unsigned char *out, const unsigned long length, 
    #           const AES_KEY *key, unsigned char ivec[AES_BLOCK_SIZE],     
    #        	  unsigned char ecount_buf[AES_BLOCK_SIZE],  unsigned int *num)
    # debug counter overflow
    ###last=self.aes_key_ctx.getCounter()[-1]
    ###before=self.getCounter()
    self._AES_ctr( ctypes.byref(block), ctypes.byref(dest), bLen, ctypes.byref(self.key), 
              ctypes.byref(self.counter), ctypes.byref(buf), ctypes.byref(num) ) 
    '''
    newlast=self.aes_key_ctx.getCounter()[-1]
    if newlast < last :
      log.warning('Counter has overflown')
      after=self.getCounter()
      log.warning('Before %s'%(before))
      log.warning('After  %s'%(after))
    '''
    ##log.debug('AFTER  %s'%( myhex(self.aes_key_ctx.getCounter())) )
    return model.array2bytes(dest)
  
  def sync(self, context):
    ''' refresh the crypto state '''
    self.aes_key_ctx = ssh_aes_ctr_ctx().fromPyObj(context.app_data)
    # we need nothing else
    self.key = self.aes_key_ctx.aes_ctx
    # copy counter content
    self.counter = self.aes_key_ctx.aes_counter
    log.info('Counter value is %s'%(myhex(self.aes_key_ctx.getCounter())) )

  def getCounter(self):
    return myhex(self.aes_key_ctx.getCounter())

  def incCounter(self):
    ctr=self.counter
    for i in range(len(ctr)-1,-1,-1):
      ctr[i] += 1
      if ctr[i] != 0:
        return
    
  def decCounter(self):
    ctr=self.counter
    for i in range(len(ctr)-1,-1,-1):
      old = ctr[i]         
      ctr[i] -= 1
      if old != 0: # underflow
        return
   
def testDecrypt():
  buf='?A\xb7\ru\xc9\x08\xe2em\x16\x06\x1a\x18\xfb\x805,\xd8\x1f\x11\xa3\x1b )G\xe2\r`\xfaw\x87\xef\xfa\xa7\x95\xe1\x84>\xe1\x90\xec\xe1\xfa\xe5\x1e\x9c\xe3'



def main(argv):
  logging.basicConfig(level=logging.INFO)
  logging.debug(argv)

  testDecrypt()
  return -1


if __name__ == "__main__":
  main(sys.argv[1:])


