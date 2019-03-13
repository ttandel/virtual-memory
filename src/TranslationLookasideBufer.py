TLB_SIZE = 4
MOST_RECENTLY_USED = TLB_SIZE - 1
LEAST_RECENTLY_USED = 0


class TranslationLookasideBufer:
	#	table entry is of the form: 	[lru, sp, f]
	# 	where lru is the least recently used info, sp is a number that is created from bits of s and p extracted from a
	#	virtual	address, and f is the starting physical address of page
	# 	specifically the page stored in pth entry of segment s's page table (i.e. f = PM[PM[s] + p]

	def __init__(self, ):
		self.table = [[LEAST_RECENTLY_USED, -2, 0] for i in range(TLB_SIZE)]

	def update_lru_fields(self, index: int, previous_lru: int) -> None:
		"""gets the table entry at 'index' and sets its LRU value to MOST_RECENTLY_USED and decrements all other LRU
		values greater than 'previous_lru' by 1"""
		for i, entry in enumerate(self.table):
			if entry[0] > previous_lru:
				entry[0] -= 1
		self.table[index][0] = MOST_RECENTLY_USED

	def get_lru(self, index: int) -> int:
		return self.table[index][0]

	def get_least_recently_used_entry(self) -> int:
		for i, entry in enumerate(self.table):
			if entry[0] == 0:
				return i
		return -1		# should never be returned as there will always be at least one entry in the table with LRU = 0

	def index_of_sp_in_table(self, sp: int) -> int:
		"""returns the index of the entry in the table if 'sp' is found in the entry; returns -1 if 'sp' is not found in
		any of the entries in the table"""
		for i, entry in enumerate(self.table):
			if entry[1] == sp:
				return i
		return -1

	def set_sp(self, index: int, sp: int) -> None:
		self.table[index][1] = sp

	def set_page_frame_address(self, index: int, page_frame_address: int) -> None:
		self.table[index][2] = page_frame_address

	def get_page_frame_address(self, index: int) -> int:
		return self.table[index][2]