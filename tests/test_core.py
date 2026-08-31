import tempfile,unittest
from pathlib import Path
from copilot.index import FilingStore,parse_document
class CoreTests(unittest.TestCase):
 def test_page_split_and_search(self):
  raw=b'<p>First page revenue 100</p><p style="page-break-after:always"> </p><p>Second page capital expenditure 25</p>'
  self.assertEqual(len(parse_document(raw,".htm")),2)
  with tempfile.TemporaryDirectory() as d:
   s=FilingStore(Path(d)); j=s.begin("test.htm"); s.process(j,raw); fid=s.status(j)["filing_id"]; _,hits=s.search(fid,"capital expenditure"); self.assertEqual(hits[0][1]["page"],2)
if __name__=="__main__":unittest.main()
