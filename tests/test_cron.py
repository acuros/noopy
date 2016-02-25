import pytest

from noopy.cron.schedule import RateEventRule, BaseEventRule, TimeEventRule


@pytest.fixture
def rate_5_mins_rule():
    return RateEventRule('5MinsRateRule', value=5)


@pytest.fixture
def time_5pm_rule():
    return TimeEventRule('5pmRule', '* 17 * * * *')


def test_rate_rule(rate_5_mins_rule):
    assert '5MinsRateRule' in BaseEventRule.rules
    assert rate_5_mins_rule.expression == 'rate(5 minutes)'


def test_time_rule(time_5pm_rule):
    assert '5MinsRateRule' in BaseEventRule.rules
    assert time_5pm_rule.expression == 'cron(* 17 * * * *)'
