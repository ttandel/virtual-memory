from bitarray import bitarray
from TranslationLookasideBufer import TranslationLookasideBufer

INIT_FILE_NAME = "input1.txt"
INPUT_FILE_NAME = "input2.txt"
OUTPUT_FILE_NAME = "913094351.txt"
OUTPUT_TLB_FILE_NAME = "913094352.txt"

SEGMENT_TABLE_SIZE = 512  # words (int)
PAGE_TABLE_SIZE = 1024  # words (int)
PAGE_SIZE = 512  # words (int)
FRAME_SIZE = 512  # words
NUM_FRAMES = 1024
PHYSICAL_MEMORY_SIZE = NUM_FRAMES * FRAME_SIZE  # = 524288 words (int)
VIRTUAL_ADDRESS_SIZE = 32  # bits
SEGMENT_TABLE_INDEX_SIZE = 9  # bits
PAGE_TABLE_INDEX_SIZE = 10  # bits
PAGE_OFFSET_SIZE = 9  # bits
PHYSICAL_ADDRESS_SIZE = 19  # bits


class PhysicalMemory:

    def __init__(self, ):
        self.PM = [0] * PHYSICAL_MEMORY_SIZE
        self.BM = bitarray(NUM_FRAMES)
        self.tlb = TranslationLookasideBufer()
        self.BM.setall(0)
        self.BM[0] = True  # the first frame is reserved for the segment table

    def find_free_page_table_frames(self) -> int:
        for index in range(len(self.BM) - 1):
            if self.BM[index] == 0 and self.BM[index + 1] == 0:
                return index
        return -1

    def find_free_page_frame(self) -> int:
        for index, bit in enumerate(self.BM):
            if bit == 0:
                return index
        return -1

    def create_blank_page_table(self, st_index: int) -> int:
        """creates a page table with all 0s and updates the segment table with the physical address to the beginning of
		the page table; returns 1 if page table was created successfully; returns -1 otherwise"""
        frame_index = self.find_free_page_table_frames()
        if frame_index == -1:
            return -1
        self.BM[frame_index: frame_index + 2] = True  # sets frame_index and frame_index + 1 to bit 1 in bitarray
        self.PM[st_index] = frame_number_to_physical_address(frame_index)
        return 1

    def create_blank_page(self, physical_address_of_page_table_entry):
        """creates a blank page and updates the page table entry with the physical address to the beginning of
		the page; returns 1 if page was created successfully; returns -1 otherwise"""
        frame_index = self.find_free_page_frame()
        if frame_index == -1:
            return -1
        self.BM[frame_index] = True
        self.PM[physical_address_of_page_table_entry] = frame_number_to_physical_address(frame_index)
        return 1

    def read_access(self, va: int) -> str:
        segment_table_index, page_table_index, page_offset = va_to_spw(va)
        segment_table_entry = self.PM[segment_table_index]
        if segment_table_entry == -1:
            return "pf"
        elif segment_table_entry == 0:
            return "err"

        page_table_entry = self.PM[segment_table_entry + page_table_index]
        if page_table_entry == -1:
            return "pf"
        elif page_table_entry == 0:
            return "err"
        # segment_table_entry = PM[s]
        # page_table_entry = PM[PM[s] + p]
        return str(page_table_entry + page_offset)  # PM[PM[s]+p] + w

    def write_access(self, va: int) -> str:
        segment_table_index, page_table_index, page_offset = va_to_spw(va)
        segment_table_entry = self.PM[segment_table_index]
        if segment_table_entry == -1:
            return "pf"
        elif segment_table_entry == 0:
            if self.create_blank_page_table(segment_table_index) == -1:
                return "err"

        physical_address_of_page_table_entry = self.PM[segment_table_index] + page_table_index
        page_table_entry = self.PM[physical_address_of_page_table_entry]
        if page_table_entry == -1:
            return "pf"
        elif page_table_entry == 0:
            if self.create_blank_page(physical_address_of_page_table_entry) == -1:
                return "err"

        return str(self.PM[self.PM[segment_table_index] + page_table_index] + page_offset)

    def read_access_with_tlb(self, va: int) -> str:
        sp, page_offset = va_to_sp_and_w(va)
        index = self.tlb.index_of_sp_in_table(sp)
        if (index != -1):  # hit
            pa = self.tlb.get_page_frame_address(index) + page_offset
            self.tlb.update_lru_fields(index, self.tlb.get_lru(index))
            return "h " + str(pa)
        else:  # miss
            pa = self.read_access(va)
            if pa == "err" or pa == "pf":  # no change to tlb
                return "m " + pa
            else:
                s, p, w = va_to_spw(va)
                index = self.tlb.get_least_recently_used_entry()
                self.tlb.set_sp(index, sp)  # update sp with new sp
                self.tlb.set_page_frame_address(index, self.PM[self.PM[s] + p])
                self.tlb.update_lru_fields(index,
                                           0)  # previous_lru = 0 because we specifically picked the index with lru = 0
                return "m " + str(pa)

    def write_access_with_tlb(self, va: int) -> str:
        sp, page_offset = va_to_sp_and_w(va)
        index = self.tlb.index_of_sp_in_table(sp)
        if (index != -1):  # hit
            pa = self.tlb.get_page_frame_address(index) + page_offset
            self.tlb.update_lru_fields(index, self.tlb.get_lru(index))
            return "h " + str(pa)
        else:
            pa = self.write_access(va)
            if pa == "err" or pa == "pf":  # no change to tlb
                return "m " + pa
            else:
                s, p, w = va_to_spw(va)
                index = self.tlb.get_least_recently_used_entry()
                self.tlb.set_sp(index, sp)  # update sp with new sp
                self.tlb.set_page_frame_address(index, self.PM[self.PM[s] + p])
                self.tlb.update_lru_fields(index,
                                           0)  # previous_lru = 0 because we specifically picked the index with lru = 0
                return "m " + str(pa)

    def init_segment_table(self, line: str) -> None:
        tokens = line.strip().split(' ')
        for i in range(0, len(tokens), 2):
            segment_table_index = int(tokens[i])
            page_table_physical_address = int(tokens[i + 1])
            page_table_frame_number = physical_address_to_frame_number(page_table_physical_address)
            self.PM[segment_table_index] = int(page_table_physical_address)
            if page_table_physical_address > 0:
                self.BM[page_table_frame_number:page_table_frame_number + 2] = True  # a page table occupies two frames

    def init_page_tables(self, line: str) -> None:
        tokens = line.strip().split(' ')
        for i in range(0, len(tokens), 3):
            page_table_index = int(tokens[i])
            segment_table_index = int(tokens[i + 1])
            if self.PM[segment_table_index] <= 0:
                return
            page_physical_address = int(tokens[i + 2])
            self.PM[self.PM[segment_table_index] + page_table_index] = page_physical_address
            if page_physical_address > 0:
                self.BM[physical_address_to_frame_number(page_physical_address)] = True

    def init_physical_memory_from_file(self):
        init_file = open(INIT_FILE_NAME, 'r')
        self.init_segment_table(init_file.readline())  # the first line has segment table info
        self.init_page_tables(init_file.readline())  # the second line has page table info
        init_file.close()

    def do_translations_from_file(self):
        input_file = open(INPUT_FILE_NAME, 'r')
        output_file = open(OUTPUT_FILE_NAME, 'w')
        output_line = ''
        va_pairs = input_file.readline().strip().split(' ')
        for i in range(0, len(va_pairs), 2):
            command = int(va_pairs[i])
            va = int(va_pairs[i + 1])
            if command == 0:
                pa = self.read_access(va)
                print('no tlb:', pa)
                output_line += pa + ' '
            elif command == 1:
                pa = self.write_access(va)
                print('no tlb:', pa)
                output_line += pa + ' '
        output_file.write(output_line.strip())

        input_file.close()
        output_file.close()

    def do_translations_from_file_with_tlb(self):
        input_file = open(INPUT_FILE_NAME, 'r')
        output_file_no_tlb = open(OUTPUT_TLB_FILE_NAME, "w")
        output_line_tlb = ''
        va_pairs = input_file.readline().strip().split(' ')
        for i in range(0, len(va_pairs), 2):
            command = int(va_pairs[i])
            va = int(va_pairs[i + 1])
            if command == 0:
                pa_tlb = self.read_access_with_tlb(va)
                print('tlb:', pa_tlb)
                output_line_tlb += pa_tlb + ' '
            elif command == 1:
                pa_tlb = self.write_access_with_tlb(va)
                print('tlb:', pa_tlb)
                output_line_tlb += pa_tlb + ' '
        output_file_no_tlb.write(output_line_tlb.strip())

        input_file.close()
        output_file_no_tlb.close()


def physical_address_to_frame_number(physical_address: int) -> int:
    return physical_address // FRAME_SIZE


def frame_number_to_physical_address(frame_number: int) -> int:
    """converts frame number to the physical address in the memory"""
    return frame_number * FRAME_SIZE


def extract(value: int, begin: int, end: int) -> int:
    """extracts [begin, end) bits from value"""
    mask = (1 << (end - begin)) - 1
    return (value >> begin) & mask


# s: segment table index
# p: page table index
# w: offset in page
def va_to_spw(va: int) -> (int, int, int):
    """returns a tuple of (s, p, w) where s: segment table index,
	p: page table index, w: offset in page"""

    page_table_index_end = PAGE_OFFSET_SIZE + PAGE_TABLE_INDEX_SIZE
    segment_table_index_end = page_table_index_end + SEGMENT_TABLE_INDEX_SIZE

    w = extract(va, 0, PAGE_OFFSET_SIZE)
    p = extract(va, PAGE_OFFSET_SIZE, page_table_index_end)
    s = extract(va, page_table_index_end, segment_table_index_end)
    return s, p, w


def va_to_sp_and_w(va: int) -> (int, int):
    """returns a tuple of (sp, w) where sp: integer that is created from the bits for s, p in the virtual address,
	w: offset in page"""

    sp_end = PAGE_OFFSET_SIZE + PAGE_TABLE_INDEX_SIZE + SEGMENT_TABLE_INDEX_SIZE
    w = extract(va, 0, PAGE_OFFSET_SIZE)
    sp = extract(va, PAGE_OFFSET_SIZE, sp_end)
    return sp, w


if __name__ == '__main__':
    memory = PhysicalMemory()
    memory.init_physical_memory_from_file()
    memory.do_translations_from_file()

    memory = PhysicalMemory()
    memory.init_physical_memory_from_file()
    memory.do_translations_from_file_with_tlb()
