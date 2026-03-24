"""Community amplification model for trust-violation word-of-mouth.

Formalizes the cascading failure described in README and Section 2.2 / 7
of the ZNP paper.

Word-of-mouth contagion model:

    A(t) = N_exit * R_social * C_trust * (1 - decay^t)

Where:
    A(t)     = cumulative influenced defections by month t
    N_exit   = number of ZNP customers who have exited
    R_social = average social reach per ZNP customer
    C_trust  = conversion rate: fraction of reached contacts who
               also defect (ZNP customers communicate with high
               credibility — Section 2.2)
    decay    = monthly decay rate of word-of-mouth influence
    t        = months since exit event

Total customer acquisition cost (CAC) impact:

    CAC_impact = A(t) * CAC_per_customer

This captures the "secondary consequences" mentioned in the README:
downstream acquisition cost from losing not just the ZNP customer
but their influenced network.

Multi-wave propagation (second-order effects):

    A_total(t) = A_1(t) + gamma * A_1(t) * R_social_2 * C_trust_2

Where:
    gamma        = probability a first-order defector also spreads WOM
    R_social_2   = social reach of influenced defectors
    C_trust_2    = conversion rate of second-order contacts (lower
                   credibility than direct ZNP testimony)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CommunityAmplificationModel:
    """Model word-of-mouth defection cascades from ZNP exits.

    Attributes:
        conversion_rate: Fraction of reached contacts who defect.
        decay_rate: Monthly decay of WOM influence (0 = no decay, 1 = instant).
        second_order_gamma: Probability that first-order defectors propagate.
        second_order_conversion: Conversion rate for second-order contacts.
    """

    conversion_rate: float = 0.08
    decay_rate: float = 0.85
    second_order_gamma: float = 0.30
    second_order_conversion: float = 0.03

    def first_order_defections(
        self,
        num_exits: int,
        avg_social_reach: int,
        months: int,
    ) -> float:
        """Compute cumulative first-order influenced defections.

        A(t) = N_exit * R_social * C_trust * (1 - decay^t)

        Args:
            num_exits: Number of ZNP customers who exited.
            avg_social_reach: Average contacts per exiting customer.
            months: Months since exit events.

        Returns:
            Expected cumulative first-order defections.
        """
        max_influenced = num_exits * avg_social_reach * self.conversion_rate
        time_factor = 1.0 - self.decay_rate ** months
        return max_influenced * time_factor

    def total_defections(
        self,
        num_exits: int,
        avg_social_reach: int,
        months: int,
        second_order_reach: int = 3,
    ) -> dict[str, float]:
        """Compute total defections including second-order propagation.

        Args:
            num_exits: Number of ZNP customers who exited.
            avg_social_reach: Average contacts per ZNP customer.
            months: Months since exit events.
            second_order_reach: Average contacts per first-order defector.

        Returns:
            Dict with first_order, second_order, and total defections.
        """
        first = self.first_order_defections(num_exits, avg_social_reach, months)
        second = (
            first
            * self.second_order_gamma
            * second_order_reach
            * self.second_order_conversion
        )

        return {
            "first_order": round(first, 2),
            "second_order": round(second, 2),
            "total": round(first + second, 2),
        }

    def cac_impact(
        self,
        num_exits: int,
        avg_social_reach: int,
        months: int,
        cac_per_customer: float,
    ) -> float:
        """Compute customer acquisition cost impact of WOM defection.

        CAC_impact = A_total(t) * CAC_per_customer

        This is the cost to replace customers lost through WOM contagion,
        on top of the direct LTV loss from the ZNP exits themselves.

        Args:
            num_exits: Number of ZNP exits.
            avg_social_reach: Contacts per ZNP customer.
            months: Months since exit events.
            cac_per_customer: Cost to acquire one replacement customer.

        Returns:
            Total CAC impact in dollars.
        """
        defections = self.total_defections(num_exits, avg_social_reach, months)
        return round(defections["total"] * cac_per_customer, 2)
