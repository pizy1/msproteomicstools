#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
=========================================================================
        msproteomicstools -- Mass Spectrometry Proteomics Tools
=========================================================================

Copyright (c) 2013, ETH Zurich
For a full list of authors, refer to the file AUTHORS.

This software is released under a three-clause BSD license:
 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
 * Neither the name of any author or any participating institution
   may be used to endorse or promote products derived from this software
   without specific prior written permission.
--------------------------------------------------------------------------
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL ANY OF THE AUTHORS OR THE CONTRIBUTING
INSTITUTIONS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
--------------------------------------------------------------------------
$Maintainer: Pedro Navarro$
$Authors: Pedro Navarro$
--------------------------------------------------------------------------
"""

from aminoacides import Aminoacides
from elements import Elements
#from spectrum import Spectrum
from types import *
import random
import sys

class Peptide:
	def __init__(self,sequence,protein="", modifications = {}): 
		self.sequence = sequence
		self.composition = self._getComposition()
		#self.modifications is a dictionary wich uses the position of the modification as key, and the delta mass as value:
		#example : GGGGMoxDDCDK  -> self.modifications = { 5 : 15.99949 , 8 : 57.02147 }
		self.modifications = {}
		if len(modifications) > 0 : self.modifications = modifications
		self.sequenceMods = self._getSequenceWithMods()
		self.mass = self._getMassFromSequence()
		self.spectra = []
		self.proteins = protein
		self.labelings = ['N15','15N','AQUA_KR','SILAC_K6R10','no_labeling','SILAC_K8R10','SILAC_K8R6']
		self.iontypes = ['a','b','c','x','y','z']
		
	def _getSequenceWithMods(self) :
		seqMods = ''
		
		for i, aa in enumerate(self.sequence[:]):
			seqMods += aa
			if i+1 in self.modifications:
				deltaMass_aaMod = self.modifications[i+1] + self.getDeltaMassFromSequence(str(aa))
				seqMods += '[' + str(deltaMass_aaMod) + ']'
				
		return seqMods
	
			
	def _getMassFromSequence(self):
		aaList = Aminoacides()

		mass = 0
		for aa in self.sequence[:]:
			for ac in aaList.list:
				if aa == ac.code:
					mass += ac.deltaMass
		
		#Adding an H2O to the mass, as it is calculated by using delta masses
		mass += (1.007825032 *2 + 15.99491462) 
		
		#Adding modifications deltamass
		for aaPosMod in self.modifications.iterkeys() :
			mass += self.modifications[aaPosMod]
		
		
		return mass
	
	def getDeltaMassFromSequence(self,sequence):
		
		aaList = Aminoacides()
		
		mass = 0
		for aa in sequence[:]:
			for ac in aaList.list:
				if aa == ac.code:
					mass += ac.deltaMass
	   
		return mass

	def pseudoreverse(self,sequence = 'None'):
		
		if sequence == 'None':        
			revseq = self.sequence[::-1][1:] + self.sequence[-1:]
			
			self.sequence = revseq
		else:
			revseq = sequence[::-1][1:] + sequence[-1:]
			
			return revseq

	def shuffle_sequence(self):

		list = []
		for aa in self.sequence[:-1]:
			list.append(aa)
			
		random.shuffle(list)

		sequence_shuffled = ''

		for aa in list:
			sequence_shuffled += aa
			
		sequence_shuffled += self.sequence[len(self.sequence)-1]

		self.sequence = sequence_shuffled
		
	def get_decoy_Q3(self,frg_serie,frg_nr,frg_z,blackList=[],max_tries = 1000):
		
		old_sequence = self.sequence

		#If b- ion and frg-nr is the second to last, it wont be impossible to get a different mass -> we use other frg_nr
		if frg_serie in ['b'] and int(frg_nr) > len(self.sequence) - 1:
			frg_nr = str (int(frg_nr)-1)
		
		try_ = 1
		found = False
		notvalid = False
		q3_decoy = 0.0
		while (try_ < max_tries and found == False):
			notvalid = False
			self.shuffle_sequence()
			q3_decoy = self.getMZfragment(frg_serie,frg_nr,frg_z)
			for q3 in blackList:
				#print abs(q3-q3_decoy)
				if abs(q3-q3_decoy) < 0.001:
					#print q3
					notvalid = True
			if notvalid == False: found = True

			try_ += 1
			
			
		self.sequence = old_sequence
		
		return q3_decoy
	
	def _getComposition(self):
		#TO-DO: it does not count the composition of modifications
		aaList = Aminoacides()
		composition = {}
		
		for aa in self.sequence[:]:
			for ac in aaList.list:
				if aa == ac.code:
					for elem,num in ac.composition.items():
						if elem not in composition:
							composition[elem] = num
						else:
							composition[elem] += num
		
		return composition
	
	def _getCompositionSeq(self,sequence):
		#TO-DO: it does not count the composition of modifications
		aaList = Aminoacides()
		composition = {}
		
		for aa in sequence[:]:
			for ac in aaList.list:
				if aa == ac.code:
					for elem,num in ac.composition.items():
						if elem not in composition:
							composition[elem] = num
						else:
							composition[elem] += num
		
		return composition
		
	
	def _getAminoacidList(self,fullList=False):
		
		aminoacides = Aminoacides()
		aaList = {}
		
		if fullList:            
			for ac in aminoacides.list:
				aaList[ac.code] = 0

		for aa in self.sequence[:]:
			for ac in aminoacides.list:
				if aa == ac.code:
					if aa not in aaList:
						aaList[aa] = 1
					else:
						aaList[aa] += 1
			
		return aaList


	def getMZ(self,charge, label = ''):
		
		#Check label
		if len(label) > 0 and label not in self.labelings : 
			print "Coding error: this labeling is not reported!! %s" % label
			sys.exit(2)
			
		
		pepmass = self._getMassFromSequence()
		z = charge
		H            = 1.007825032
		massC        = 12.0000000
		massProton   =  1.0072765
		massN        = 14.00307401
		massC13      = 13.003355
		massN15      = 15.0001089
		massShiftN15 = massN15 - massN
		massShiftC13 = massC13 - massC
		
		
		
		# N15 labeling: adds up the shift mass
		shift = 0.0
		if label == '15N' or label == 'N15' :
			composition = self._getComposition()
			if 'N' in composition:
				shift = (float(composition['N']) * massShiftN15) 
				
		#AQUA_KR labeling: adds up the shift mass
		if label == 'AQUA_KR':
			#Update (23.nov.2010): AQUA_KR only modifies Lys and Arg in the C-terminal position.  
			if 'K' in self.sequence[-1:] : shift += 6 * massShiftC13 + 2 * massShiftN15
			if 'R' in self.sequence[-1:] : shift += 6 * massShiftC13 + 4 * massShiftN15

		if label == 'SILAC_K6R10' :
			#All K and R amino acides are shifted 6 Da and 10 Da.
			numK = 0
			numR = 0
			for aa in self.sequence[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			shift += numK * ( 6 * massShiftC13 ) 
			shift += numR * ( 6 * massShiftC13 + 4 * massShiftN15 )

		if label == 'SILAC_K8R10' :
			#All K and R amino acides are shifted 8 Da and 10 Da.
			numK = 0
			numR = 0
			for aa in self.sequence[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			shift += numK * ( 6 * massShiftC13  + 2 * massShiftN15 ) 
			shift += numR * ( 6 * massShiftC13  + 4 * massShiftN15 )
			
		if label == 'SILAC_K8R6' :
			#All K and R amino acides are shifted 8 and 6 Da.
			numK = 0
			numR = 0
			for aa in self.sequence[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			shift += numK * ( 6 * massShiftC13 + 2 * massShiftN15 )
			shift += numR * ( 6 * massShiftC13 )

 
		mz = (pepmass + shift + massProton*z)/z
	   
		return mz
	
	def getMZfragment(self,ion_type,ion_number,ion_charge, label = '', fragmentlossgain = 0.0):
		#Check label
		if len(label) > 0 and label not in self.labelings : 
			print "Coding error: this labeling is not reported!! %s" % label
			sys.exit(2)
		
		#Check ion type
		#if ion_type not in self.iontypes :
			#print "This ion type can not be processed :" , ion_type
			#print "This is the list of ion types considered in this library : " , self.iontypes
			#sys.exit(2)
		
		massH      =  1.007825032
		massO      = 15.99491462
		massN      = 14.00307401
		massC      = 12.0000000
		massProton =  1.0072765
		massNH3    = massN + 3 * massH
		massH2O    = (massH *2 + massO) 
		massCO2		= (massC + 2 * massO)
		protonMass = 1.007825032

		massN15 = 15.0001089
		massShiftN15 = massN15 - massN
		massC13 = 13.003355
		massShiftC13 = massC13 - massC
	   
		frg_number = int(ion_number)
		frg_charge = int(ion_charge)    
		
		mzfragment = 0
		frg_seq = ''

		#precursors
		if ion_type == 'p' :
			mzfragment = self.getMZ(frg_charge, label)
			return mzfragment
		
		#a series
		if ion_type == 'a' :
			frg_seq = self.sequence[:frg_number] 
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			mzfragment -= (massC + massO)
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if aaPosMod <= frg_number: mzfragment += self.modifications[aaPosMod]

		#b series
		if ion_type == 'b' :
			frg_seq = self.sequence[:frg_number] 
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if aaPosMod <= frg_number: mzfragment += self.modifications[aaPosMod]
		
		#c series
		if ion_type == 'c' :
			frg_seq = self.sequence[:frg_number] 
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			mzfragment += massNH3
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if aaPosMod <= frg_number: mzfragment += self.modifications[aaPosMod]
		
		#x series
		if ion_type == 'x' :
			frg_seq = self.sequence[-frg_number:]
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			mzfragment += massCO2
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if ( len(self.sequence) - frg_number ) < aaPosMod : mzfragment += self.modifications[aaPosMod]


		#y series
		if ion_type == 'y' :
			frg_seq = self.sequence[-frg_number:]
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			mzfragment += massH2O
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if ( len(self.sequence) - frg_number ) < aaPosMod : mzfragment += self.modifications[aaPosMod]

		#z series
		if ion_type == 'z' :
			frg_seq = self.sequence[-frg_number:]
			mzfragment = self.getDeltaMassFromSequence(frg_seq)
			mzfragment += massH2O
			mzfragment -= massNH3
			#Adding modifications deltamass
			for aaPosMod in self.modifications.iterkeys() :
				if ( len(self.sequence) - frg_number ) < aaPosMod : mzfragment += self.modifications[aaPosMod]

			
		# 15N labeling: adds up the shift mass
		if label == '15N' or label == 'N15':
			frg_composition = self._getCompositionSeq(frg_seq)
			if 'N' in frg_composition:
				shift = (float(frg_composition['N']) * massShiftN15) 
				mzfragment += shift
				
		#AQUA_KR labeling: adds up the shift mass
		if label == 'AQUA_KR':
			#Update (23.nov.2010): AQUA_KR only modifies Lys and Arg in the C-terminal position. 
			#Update (1.dec.2010) : I am a jerk. I should have taken it only for y ions , and not for the b ones 
			if 'K' in self.sequence[-1:] and ion_type == 'y' : mzfragment += 6 * massShiftC13 + 2 * massShiftN15
			if 'R' in self.sequence[-1:] and ion_type == 'y' : mzfragment += 6 * massShiftC13 + 4 * massShiftN15
		
		if label == 'SILAC_K6R10' :
			#All K and R amino acides are shifted 6 Da and 10 Da.
			numK = 0
			numR = 0
			for aa in frg_seq[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			mzfragment += numK * ( 6 * massShiftC13 )
			mzfragment += numR * ( 6 * massShiftC13 + 4 * massShiftN15 )
		
		if label == 'SILAC_K8R10' :
			#All K and R amino acides are shifted 8 Da and 10 Da.
			numK = 0
			numR = 0
			for aa in frg_seq[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			mzfragment += numK * ( 6 * massShiftC13  + 2 * massShiftN15 ) 
			mzfragment += numR * ( 6 * massShiftC13  + 4 * massShiftN15 )

		if label == 'SILAC_K8R6' :
			#All K and R amino acides are shifted 8 Da and 6 Da.
			numK = 0
			numR = 0
			for aa in frg_seq[:] :
				if aa == 'K' : numK += 1
				if aa == 'R' : numR += 1
			mzfragment += numK * ( 6 * massShiftC13  + 2 * massShiftN15 ) 
			mzfragment += numR * ( 6 * massShiftC13 )


		mzfragment += frg_charge * massProton
		mzfragment += fragmentlossgain
		mzfragment /= frg_charge
		
		return mzfragment
	
	
	
	def addSpectrum(self,spectrum):
		'''Deprecated definition'''
		if isinstance(spectrum,Spectrum):
			self.spectra.append(spectrum)
		#else: #catch error


def test():

	mypep = Peptide('LIGPTSVVMGR',modifications = {9:15.99491462})
	mypep2 = Peptide('LIGPTSVVMGR')
	
	for pep in [mypep,mypep2] : 
			
		print pep.sequence, pep.mass, pep.modifications
		print pep._getComposition()
		print pep._getAminoacidList(True)
		
		print pep.getMZ(1)
		
		print '#,' , ", ".join(pep.iontypes)
		masses = []
		for v in range(1,len(pep.sequence)+1) :
			masses.append(str(v))
			for ionserie in pep.iontypes :
				masses.append(str(pep.getMZfragment(ionserie,v,1)))
			print ", ".join(masses)
			masses = []
			
			#for property, value in vars(pep).iteritems() :
			#	print property , " : " , value

	
   

if __name__ == "__main__":
	test()
	sys.exit(2)
