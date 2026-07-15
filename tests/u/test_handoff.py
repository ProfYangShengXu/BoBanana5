"""
Bobanana 5.0 — Unit: Handoff Ticket
测试 handoff_ticket.py 的核心功能。
"""
import os, sys, json, time, tempfile, shutil, unittest

sys.path.insert(0, '.')
import handoff_ticket as ht

class TestHandoffTicket(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.orig_dir = ht.HANDOFF_DIR
        ht.HANDOFF_DIR = self.tmpdir

    def tearDown(self):
        ht.HANDOFF_DIR = self.orig_dir
        shutil.rmtree(self.tmpdir)

    def test_create_ticket(self):
        ticket = ht.create_handoff_ticket("boss", "architect", artifacts=["prd.md"], pending_decisions=["need tech review"])
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket['sender_id'], 'boss')
        self.assertEqual(ticket['receiver_id'], 'architect')
        self.assertIn('prd.md', ticket['artifacts'])
        self.assertIn('need tech review', ticket['pending_decisions'])

    def test_create_with_risks(self):
        risks = [{"risk": "deadline", "level": "high"}]
        ticket = ht.create_handoff_ticket("dev", "test", risks=risks)
        self.assertEqual(ticket['risks'], risks)

    def test_handoff_id_unique(self):
        import time
        t1 = ht.create_handoff_ticket("boss", "architect")
        time.sleep(0.002)
        t2 = ht.create_handoff_ticket("architect", "dev")
        self.assertNotEqual(t1['ticket_id'], t2['ticket_id'])

    def test_get_nonexistent_ticket(self):
        result = ht.get_handoff_ticket("ht-nonexistent")
        self.assertIsNone(result)

    def test_create_with_assumptions(self):
        ticket = ht.create_handoff_ticket("alice", "bob", assumptions=["network available"])
        self.assertIn("network available", ticket['assumptions'])

if __name__ == '__main__':
    unittest.main()
