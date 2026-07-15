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

    def test_create_ticket_with_risk_tags(self):
        risks = [{"risk": "deadline", "level": "high"}]
        ticket = ht.create_handoff_ticket("dev", "test", risk_tags=risks)
        self.assertEqual(ticket['risk_tags'], risks)

    def test_handoff_chain(self):
        t1 = ht.create_handoff_ticket("boss", "architect")
        t2 = ht.create_handoff_ticket("architect", "dev")
        self.assertTrue(t2['version'] > t1['version'])

    def test_get_no_ticket(self):
        result = ht.get_handoff_tickets("ghost_role")
        self.assertEqual(result['total'], 0)

    def test_version_timestamp(self):
        v = ht._next_version("test")
        self.assertGreater(v, int(time.time() * 1000) - 5000)

    def test_create_with_badcase(self):
        badcases = [{"desc": "API返回错误", "reproduce": "GET /api/test"}]
        ticket = ht.create_handoff_ticket("test", "dev", badcases=badcases)
        self.assertEqual(ticket['badcases'], badcases)

if __name__ == '__main__':
    unittest.main()
