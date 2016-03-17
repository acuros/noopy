import pytest

from noopy.cron.rule import RateEventRule, BaseEventRule, TimeEventRule
from noopy.decorators import cron


@pytest.fixture
def rate_5_mins_rule():
    return RateEventRule('5MinsRateRule', value=5)


@pytest.fixture
def time_5pm_rule():
    return TimeEventRule('5pmRule', '* 17 * * * *')


@pytest.fixture
def cronjob():
    return lambda event, context: dict(foo='bar')


def test_rate_rule(rate_5_mins_rule):
    assert len(BaseEventRule.rules) == 0
    assert rate_5_mins_rule.expression == 'rate(5 minutes)'


def test_time_rule(time_5pm_rule):
    assert len(BaseEventRule.rules) == 0
    assert time_5pm_rule.expression == 'cron(* 17 * * * *)'


def test_cron_decorator(cronjob):
    rule = RateEventRule("RateCron", 1, RateEventRule.UNIT_HOURS)
    cron(rule)(cronjob)
    assert len(BaseEventRule.rules) == 1
    assert len(BaseEventRule.rules.values()[0].functions) == 1
    assert BaseEventRule.rules.values()[0].functions[0] == cronjob
