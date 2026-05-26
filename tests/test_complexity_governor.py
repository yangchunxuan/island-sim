from systems.complexity_governor import (
    ComplexityGovernor,
    GovernorVerdict,
    MechanismCategory,
    ALLOWED_DYNAMICS,
)


class TestComplexityGovernor:
    def setup_method(self):
        self.governor = ComplexityGovernor()

    def test_approve_fertility_mechanism(self):
        verdict = self.governor.evaluate({
            'name': 'fertility_system',
            'description': 'Fertility dynamics based on humidity',
            'affects_dynamics': ['fertility'],
        })
        assert verdict.approved is True
        assert verdict.category == MechanismCategory.DYNAMICS

    def test_approve_migration_mechanism(self):
        verdict = self.governor.evaluate({
            'name': 'migration_system',
            'description': 'NPC migration between regions',
            'affects_dynamics': ['migration'],
        })
        assert verdict.approved is True
        assert verdict.category == MechanismCategory.DYNAMICS

    def test_reject_furniture(self):
        verdict = self.governor.evaluate({
            'name': 'furniture_system',
            'description': 'Add furniture to houses',
            'affects_dynamics': ['furniture'],
        })
        assert verdict.approved is False
        assert verdict.category == MechanismCategory.COSMETIC

    def test_reject_empty_dynamics(self):
        verdict = self.governor.evaluate({
            'name': 'empty_proposal',
            'description': 'No dynamics affected',
            'affects_dynamics': [],
        })
        assert verdict.approved is False
        assert verdict.category == MechanismCategory.COSMETIC

    def test_mixed_dynamics_cosmetic(self):
        verdict = self.governor.evaluate({
            'name': 'mixed_system',
            'description': 'Fertility with furniture',
            'affects_dynamics': ['fertility', 'furniture'],
        })
        assert verdict.approved is True
        assert verdict.category == MechanismCategory.DYNAMICS

    def test_unknown_dynamics(self):
        verdict = self.governor.evaluate({
            'name': 'unknown_system',
            'description': 'Random unknown dynamics',
            'affects_dynamics': ['random_stuff'],
        })
        assert verdict.approved is False
        assert verdict.category == MechanismCategory.COSMETIC

    def test_verdict_to_dict(self):
        verdict = GovernorVerdict(
            approved=True,
            category=MechanismCategory.DYNAMICS,
            reason='Test reason',
        )
        d = verdict.to_dict()
        assert d == {'approved': True, 'category': 'dynamics', 'reason': 'Test reason'}

    def test_all_allowed_dynamics_pass(self):
        for dyn in ALLOWED_DYNAMICS:
            verdict = self.governor.evaluate({
                'name': f'{dyn}_system',
                'description': f'{dyn} dynamics',
                'affects_dynamics': [dyn],
            })
            assert verdict.approved is True, f'{dyn} should be approved'
            assert verdict.category == MechanismCategory.DYNAMICS, f'{dyn} should be DYNAMICS'
